"""Authenticated sportsbook APIs backed by the server-side OpticOdds client.

These endpoints are intentionally separate from the stock prediction APIs. An
OpticOdds selection is not a ``betengine.Market`` and must not be coerced into
the stock over/under schema. The record endpoint stores a comparison snapshot
for every leg and returns the server-calculated parlay maths.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from admin_panel.models import OpticOddsBetMonitor, SportsbookBetSlip
from admin_panel.optic_odds import OpticOddsClient, OpticOddsError, default_sportsbooks


def _error(exc: OpticOddsError) -> Response:
    return Response({"detail": str(exc)}, status=getattr(exc, "status_code", 502))


def _configured_books() -> list[str]:
    configured = getattr(settings, "OPTIC_ODDS_COMPARISON_SPORTSBOOKS", []) or default_sportsbooks()
    primary = getattr(settings, "OPTIC_ODDS_PRIMARY_SPORTSBOOK", "hardrockbet")
    return list(dict.fromkeys([str(primary).lower(), *[str(book).lower() for book in configured]]))[:5]


def _books(request, body=None) -> list[str]:
    body = body or {}
    raw = request.query_params.get("sportsbooks", "") or body.get("sportsbooks", "")
    if isinstance(raw, list):
        requested = [str(book).strip().lower() for book in raw if str(book).strip()]
    else:
        requested = [part.strip().lower() for part in str(raw).split(",") if part.strip()]
    # The chatbot monitor is the source of truth for comparison-book
    # selection. It forwards its saved list in the trusted server request;
    # retain the configured list as the safe default when no list is supplied.
    allowed = list(dict.fromkeys([*_configured_books(), *requested]))
    selected = [book for book in dict.fromkeys(requested or allowed) if book in allowed]
    primary = str(getattr(settings, "OPTIC_ODDS_PRIMARY_SPORTSBOOK", "hardrockbet")).lower()
    return list(dict.fromkeys([primary, *selected]))[:5]


def _decimal(value) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
        return parsed if parsed > 1 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _matching(rows, market, selection):
    market = "".join(ch for ch in str(market).strip().lower() if ch.isalnum())
    selection = str(selection).strip().lower()
    return [
        row for row in rows
        if "".join(ch for ch in str(row.get("market", "")).strip().lower() if ch.isalnum()) == market
        and str(row.get("selection", "")).strip().lower() == selection
    ]


def _comparison(matching, primary=None):
    primary = str(primary or getattr(settings, "OPTIC_ODDS_PRIMARY_SPORTSBOOK", "hardrockbet")).strip().lower()
    provider_odds = {}
    raw_by_provider = {}
    for row in matching:
        provider = str(row.get("sportsbook", "")).lower()
        decimal = _decimal(row.get("decimal"))
        if provider and decimal is not None:
            provider_odds[provider] = {"price": row.get("price"), "decimal": float(decimal), "decimal_raw": str(decimal)}
            raw_by_provider[provider] = row
    primary_line = provider_odds.get(primary)
    if not primary_line:
        return None
    peers = [Decimal(str(line.get("decimal_raw", line["decimal"]))) for book, line in provider_odds.items() if book != primary]
    primary_decimal = Decimal(str(primary_line.get("decimal_raw", primary_line["decimal"])))
    aggregate_comp_odds = sum((Decimal("1") / decimal for decimal in peers), Decimal("0")) / len(peers) if peers else None
    ev_odds = (Decimal("1") / primary_decimal - aggregate_comp_odds) if aggregate_comp_odds is not None else None
    lowest = min(peers) if peers else None
    highest = max(peers) if peers else None
    edge = round(float(primary_decimal - lowest), 4) if lowest is not None else None
    relative = (Decimal(str(edge)) / lowest) if edge is not None and lowest else Decimal("0")
    above_all = highest is not None and primary_decimal > highest
    significant = edge is not None and Decimal(str(edge)) >= Decimal(str(getattr(settings, "OPTIC_ODDS_AUDIT_MIN_DECIMAL_GAP", 0.20))) and relative >= Decimal(str(getattr(settings, "OPTIC_ODDS_AUDIT_MIN_RELATIVE_GAP", 0.10)))
    flagged = bool(above_all or significant)
    reason = "Higher than every selected provider" if above_all else ("Significantly above the lowest selected price" if significant else "Within the selected market range")
    probability = sum((Decimal("1") / Decimal(str(line.get("decimal_raw", line["decimal"]))) for line in provider_odds.values()), Decimal("0")) / len(provider_odds) if provider_odds else None
    return {
        "provider_odds": provider_odds,
        "raw_by_provider": raw_by_provider,
        "primary": primary_line,
        "weighted_implied_probability": round(float(probability), 6) if probability is not None else None,
        "fair_decimal": round(float(Decimal("1") / probability), 4) if probability else None,
        "aggregate_comp_odds": round(float(aggregate_comp_odds), 6) if aggregate_comp_odds is not None else None,
        "aggregate_comp_odds_raw": aggregate_comp_odds,
        "ev_odds": round(float(ev_odds), 6) if ev_odds is not None else None,
        "ev_odds_raw": ev_odds,
        "edge_decimal": edge,
        "is_potentially_bad": flagged,
        "audit_reason": reason,
    }


def _leg_payload(leg, result, event="", wager_amount=Decimal("0"), primary=None):
    primary = str(primary or getattr(settings, "OPTIC_ODDS_PRIMARY_SPORTSBOOK", "hardrockbet")).strip().lower()
    peers = ", ".join(f"{book.title()}: {line['decimal']:.2f}" for book, line in result["provider_odds"].items() if book != primary)
    comparison = f" vs. {peers}" if peers else " (no peer quote available)"
    audit = f"Review: {result['audit_reason']}" if result["is_potentially_bad"] else "Within range"
    ev_odds = result.get("ev_odds")
    ev_odds_raw = result.get("ev_odds_raw", ev_odds)
    # Cash EV follows the readout: stake multiplied by the leg's EV_ODDS.
    # The displayed EV_ODDS is rounded, so use the raw value for the cents
    # calculation and avoid compounding display-rounding error.
    ev_amount = (wager_amount * Decimal(str(ev_odds_raw))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if ev_odds_raw is not None else None
    ev_text = f" | EV_ODDS: {ev_odds:+.6f} · EV_AMT: ${ev_amount:,.2f}" if ev_odds is not None and ev_amount is not None else " | EV unavailable (no peer price)"
    primary_name = "Hard Rock" if primary in {"hardrockbet", "hardrock"} else primary.replace("_", " ").title()
    note = f"{event or leg.get('event') or leg.get('selection')} | {primary_name} {result['primary']['decimal']:.2f}{comparison} | Aggregate comp odds: {result.get('aggregate_comp_odds') if result.get('aggregate_comp_odds') is not None else '—'}{ev_text} | {audit}"
    return {
        "fixture_id": str(leg.get("fixture_id", "")),
        "event": event or leg.get("event") or "",
        "sport": leg.get("sport") or "",
        "league": leg.get("league") or "",
        "market": leg.get("market") or "",
        "selection": leg.get("selection") or "",
        "primary_sportsbook": primary,
        "primary_decimal": result["primary"]["decimal"],
        "provider_odds": result["provider_odds"],
        "weighted_implied_probability": result["weighted_implied_probability"],
        "fair_decimal": result["fair_decimal"],
        "aggregate_comp_odds": result["aggregate_comp_odds"],
        "ev_odds": ev_odds,
        "ev_amount": float(ev_amount) if ev_amount is not None else None,
        "edge_decimal": result["edge_decimal"],
        "is_potentially_bad": result["is_potentially_bad"],
        "audit_reason": result["audit_reason"],
        "note": note,
    }


def _parlay_comparison(leg_records, baseline=None):
    """Calculate parlay EV from each peer's combined price.

    A peer is eligible only when it has a valid decimal quote for every leg.
    Each eligible peer receives equal weight, exactly as in the supplied
    calculation readout.
    """
    baseline = str(baseline or getattr(settings, "OPTIC_ODDS_PRIMARY_SPORTSBOOK", "hardrockbet")).strip().lower()
    if not leg_records:
        return None
    peer_sets = [set(leg.get("provider_odds", {})) - {baseline} for leg in leg_records]
    common_peers = set.intersection(*peer_sets) if peer_sets else set()
    if not common_peers:
        return None
    baseline_combined = Decimal("1")
    for leg in leg_records:
        baseline_line = leg.get("provider_odds", {}).get(baseline, {})
        baseline_combined *= Decimal(str(baseline_line.get("decimal_raw", leg["primary_decimal"])))
    peer_combined = {}
    for provider in sorted(common_peers):
        combined = Decimal("1")
        for leg in leg_records:
            combined *= Decimal(str(leg["provider_odds"][provider].get("decimal_raw", leg["provider_odds"][provider]["decimal"])))
        peer_combined[provider] = combined
    aggregate_raw = sum((Decimal("1") / combined for combined in peer_combined.values()), Decimal("0")) / len(peer_combined)
    baseline_probability = Decimal("1") / baseline_combined
    ev_raw = baseline_probability - aggregate_raw
    return {
        "baseline_combined": baseline_combined,
        "peer_combined": peer_combined,
        "aggregate_comp_odds_raw": aggregate_raw,
        "aggregate_comp_odds": round(float(aggregate_raw), 6),
        "ev_odds_raw": ev_raw,
        "ev_odds": round(float(ev_raw), 6),
    }


class SportsbookCatalogView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            client = OpticOddsClient()
            return Response({"sports": client.sports(), "providers": _configured_books()})
        except OpticOddsError as exc:
            return _error(exc)


class SportsbookLeaguesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            return Response({"leagues": OpticOddsClient().leagues(request.query_params.get("sport"))})
        except OpticOddsError as exc:
            return _error(exc)


class SportsbookFixturesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        sport = request.query_params.get("sport")
        league = request.query_params.get("league")
        if not sport or not league:
            return Response({"detail": "sport and league are required."}, status=status.HTTP_400_BAD_REQUEST)
        live_only = request.query_params.get("live_only", "false").lower() == "true"
        try:
            # Keep the default response focused on genuinely upcoming events.
            # Without an explicit lower bound OpticOdds may return a large
            # historical/prematch catalogue, which makes the first page feel
            # like it is still loading and can hide the useful fixtures.
            start_after = request.query_params.get("start_date_after")
            if not live_only and not start_after:
                start_after = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            fixtures = OpticOddsClient().fixtures(
                sport=sport,
                league=league,
                live_only=live_only,
                start_date_after=start_after,
                start_date_before=request.query_params.get("start_date_before"),
            )
            return Response({"fixtures": fixtures, "count": len(fixtures)})
        except OpticOddsError as exc:
            return _error(exc)


class SportsbookOddsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, fixture_id):
        books = _books(request)
        try:
            rows = OpticOddsClient().odds(fixture_id, books, market=request.query_params.get("market", "moneyline"))
            return Response({"fixture_id": fixture_id, "sportsbooks": books, "odds": rows})
        except OpticOddsError as exc:
            return _error(exc)


class SportsbookRecordBetSlipView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        legs = data.get("legs")
        if not isinstance(legs, list) or not 1 <= len(legs) <= 20:
            return Response({"detail": "Add between 1 and 20 selections to the betslip."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            stake = Decimal(str(data.get("stake")))
        except (InvalidOperation, TypeError, ValueError):
            stake = Decimal("0")
        if stake <= 0:
            return Response({"detail": "Stake must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)

        books = _books(request, data)
        primary = str(getattr(settings, "OPTIC_ODDS_PRIMARY_SPORTSBOOK", "hardrockbet")).strip().lower()
        client = OpticOddsClient()
        leg_records = []
        comparison_notes = []
        leg_ev_odds = []
        leg_ev_amounts = []
        leg_aggregate_comp_odds = []
        combined = Decimal("1")
        try:
            for leg in legs:
                fixture_id = str(leg.get("fixture_id") or "").strip()
                market = str(leg.get("market") or "moneyline").strip()
                selection = str(leg.get("selection") or "").strip()
                if not fixture_id or not selection:
                    return Response({"detail": "Each leg needs a fixture_id, market and selection."}, status=status.HTTP_400_BAD_REQUEST)
                rows = leg.get("odds_snapshot") if isinstance(leg.get("odds_snapshot"), list) else []
                snapshot_books = {str(row.get("sportsbook", "")).strip().lower() for row in rows if isinstance(row, dict)}
                # The betting UI intentionally sends only Hard Rock. Fetch a
                # fresh comparison snapshot here using the books selected in
                # the chatbot monitor settings before writing the audit record.
                if not rows or any(book not in snapshot_books for book in books):
                    rows = client.odds(fixture_id, books, market=market)
                result = _comparison(_matching(rows, market, selection), primary=primary)
                if not result:
                    return Response({"detail": f"Hard Rock odds are unavailable for {selection}."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                event = str(leg.get("event") or "")
                payload = _leg_payload({**leg, "fixture_id": fixture_id, "market": market, "selection": selection}, result, event, stake, primary=primary)
                leg_records.append({**payload, "odds_snapshot": _matching(rows, market, selection)})
                comparison_notes.append(payload["note"])
                leg_ev_odds.append(payload["ev_odds"])
                leg_ev_amounts.append(payload["ev_amount"])
                leg_aggregate_comp_odds.append(payload["aggregate_comp_odds"])
                combined *= Decimal(str(result["primary"].get("decimal_raw", result["primary"]["decimal"])))
            # Keep enough precision for the reciprocal calculations. The UI
            # can round this for display, but EV must use the full combined
            # Hard Rock price.
            combined = combined.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
            payout = (stake * combined).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            parlay_comparison = _parlay_comparison(leg_records) if len(leg_records) > 1 else None
            if len(leg_records) > 1:
                combined_ev_odds = parlay_comparison["ev_odds"] if parlay_comparison else None
                combined_ev_amount = (stake * parlay_comparison["ev_odds_raw"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if parlay_comparison else None
            else:
                combined_ev_odds = leg_ev_odds[0] if leg_ev_odds and leg_ev_odds[0] is not None else None
                combined_ev_amount = Decimal(str(leg_ev_amounts[0])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if leg_ev_amounts and leg_ev_amounts[0] is not None else None
            if len(leg_records) > 1:
                parlay_text = (
                    f"Parlay comparison ({len(leg_records)} legs) | Hard Rock combined odds: {combined:.8f}"
                    f" | Aggregate comp odds: {parlay_comparison['aggregate_comp_odds']:.6f}"
                    f" | Parlay EV_ODDS: {combined_ev_odds:+.6f} · Parlay EV_AMT: ${combined_ev_amount:,.2f}"
                    if parlay_comparison and combined_ev_amount is not None
                    else f"Parlay comparison ({len(leg_records)} legs) | Hard Rock combined odds: {combined:.8f} | EV unavailable (one or more providers lack a complete parlay quote)"
                )
                for leg in leg_records:
                    # Keep individual EV fields on each monitor row for the
                    # expandable leg details, while using one combined note
                    # for the collapsed parlay card.
                    leg["note"] = parlay_text
                comparison_notes = [leg["note"] for leg in leg_records]
            slip = SportsbookBetSlip.objects.create(user=request.user, stake=stake, combined_decimal_odds=combined, aggregate_comp_odds=parlay_comparison["aggregate_comp_odds"] if parlay_comparison else None, potential_payout=payout, ev_odds=combined_ev_odds, ev_amount=combined_ev_amount, leg_aggregate_comp_odds=leg_aggregate_comp_odds, leg_count=len(leg_records), legs=leg_records, comparison_notes=comparison_notes)
            for leg in leg_records:
                OpticOddsBetMonitor.objects.create(
                    admin_user=request.user,
                    sportsbook_slip=slip,
                    fixture_id=leg["fixture_id"], event=leg["event"], sport=leg["sport"], league=leg["league"], market=leg["market"], selection=leg["selection"],
                    primary_sportsbook=primary, primary_price=str(leg["provider_odds"][primary].get("price", "")), primary_decimal=leg["primary_decimal"], stake=stake,
                    provider_odds=leg["provider_odds"], provider_weights={book: 1 / len(leg["provider_odds"]) for book in leg["provider_odds"]}, weighted_implied_probability=leg["weighted_implied_probability"], fair_decimal=leg["fair_decimal"],
                    aggregate_comp_odds=leg["aggregate_comp_odds"], ev_odds=leg["ev_odds"], ev_amount=leg["ev_amount"],
                    is_potentially_bad=leg["is_potentially_bad"], audit_reason=leg["audit_reason"], edge_decimal=leg["edge_decimal"], note=leg["note"], odds_snapshot=leg["odds_snapshot"],
                )
            return Response({"status": "recorded", "slip_id": slip.id, "stake": str(stake), "combined_decimal_odds": str(combined), "aggregate_comp_odds": slip.aggregate_comp_odds, "potential_payout": str(payout), "ev_odds": combined_ev_odds, "ev_amount": str(combined_ev_amount) if combined_ev_amount is not None else None, "leg_ev_odds": leg_ev_odds, "leg_aggregate_comp_odds": leg_aggregate_comp_odds, "leg_count": len(leg_records), "legs": leg_records, "comparison_notes": comparison_notes, "simulation": True}, status=status.HTTP_201_CREATED)
        except OpticOddsError as exc:
            return _error(exc)
