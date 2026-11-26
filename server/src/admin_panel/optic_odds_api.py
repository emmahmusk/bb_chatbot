from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_panel.models import DemoOddsOverride, OpticOddsBetMonitor, SportsbookBetSlip
from admin_panel.optic_odds import OpticOddsClient, OpticOddsError, default_sportsbooks, DEMO_SPORTS, DEMO_LEAGUES, demo_fixtures, demo_odds
from admin_panel.permissions import IsAdminOrServiceKey
from admin_panel.odds_preferences import preference_payload, saved_preference

logger = logging.getLogger(__name__)
User = get_user_model()


def _primary_sportsbook() -> str:
    return str(getattr(settings, "OPTIC_ODDS_PRIMARY_SPORTSBOOK", "draftkings") or "draftkings").strip().lower()


def _primary_label() -> str:
    return str(getattr(settings, "OPTIC_ODDS_PRIMARY_SPORTSBOOK_LABEL", "DraftKings") or "DraftKings").strip() or "DraftKings"


EDGE_METHODOLOGY = (
    "Edge is the baseline decimal price minus the lowest valid peer decimal price. "
    "A note is flagged when the baseline is above every valid peer, or at least "
    "the configured decimal and relative thresholds above the lowest peer."
)


def _risk_fields(ev_odds, ev_amount):
    return {
        "prime_risk_margin": (float(ev_odds) * 100) if ev_odds is not None else None,
        "prime_risk_margin_decimal": float(ev_odds) if ev_odds is not None else None,
        "prime_risk_dollar_value": str(ev_amount) if ev_amount is not None else None,
    }


def _error(exc: OpticOddsError) -> Response:
    return Response({"detail": str(exc)}, status=exc.status_code)


def _books(request, body=None) -> list[str]:
    body = body or {}
    raw = request.query_params.get("sportsbooks", "") or body.get("sportsbooks", "")
    if isinstance(raw, list):
        return list(dict.fromkeys([str(x).strip().lower() for x in raw if str(x).strip()]))[:5] or default_sportsbooks()
    requested = [x.strip().lower() for x in raw.split(",") if x.strip()]
    return list(dict.fromkeys(requested or default_sportsbooks()))[:5]


def _weighted(rows: list[dict], weights: dict) -> tuple[dict, float | None, float | None]:
    provider_odds = {}
    valid = {}
    for row in rows:
        decimal = row.get("decimal")
        if decimal and float(decimal) > 1:
            provider = str(row.get("sportsbook", "")).lower()
            provider_odds[provider] = {"price": row.get("price"), "decimal": float(decimal)}
            valid[provider] = float(decimal)
    if not valid:
        return provider_odds, None, None
    if not isinstance(weights, dict):
        weights = {}
    if not weights or not any(str(provider) in weights for provider in valid):
        weights = {provider: 1 / len(valid) for provider in valid}
    else:
        # Unspecified books share the remaining weight equally; this avoids a
        # surprising zero contribution when the UI sends only one override.
        supplied = {provider: float(weights.get(provider, 0) or 0) for provider in valid}
        missing = [provider for provider, value in supplied.items() if value <= 0]
        remaining = max(0.0, 1.0 - sum(value for value in supplied.values() if value > 0))
        for provider in missing:
            supplied[provider] = remaining / len(missing) if missing else 0
        weights = supplied
    total_weight = sum(float(weights.get(provider, 0)) for provider in valid)
    if total_weight <= 0:
        weights = {provider: 1 / len(valid) for provider in valid}
        total_weight = 1
    normalised = {provider: float(weights.get(provider, 0)) / total_weight for provider in valid}
    probability = sum(normalised[provider] * (1 / decimal) for provider, decimal in valid.items())
    return provider_odds, round(probability, 6), round(1 / probability, 4) if probability else None


def _normalise_peer_weights(providers, supplied=None):
    providers = list(dict.fromkeys(str(provider).strip().lower() for provider in providers if str(provider).strip()))
    supplied = supplied if isinstance(supplied, dict) else {}
    values = {}
    for provider in providers:
        try:
            value = float(supplied.get(provider, 0))
            values[provider] = max(0.0, value) if value == value and value != float("inf") else 0.0
        except (TypeError, ValueError):
            values[provider] = 0.0
    total = sum(values.values())
    if total > 1.000001:
        values = {provider: value / 100 for provider, value in values.items()}
        total = sum(values.values())
    if total <= 0:
        return {provider: 1 / len(providers) for provider in providers} if providers else {}
    return {provider: value / total for provider, value in values.items() if value > 0}


class OpticOddsBaseView(APIView):
    permission_classes = [IsAdminOrServiceKey]

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if response is not None:
            return response
        logger.exception("Unhandled OpticOdds admin API error")
        return Response({
            "detail": "The admin OpticOdds service failed while processing the request.",
            "error_type": exc.__class__.__name__,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminOpticOddsSportsView(OpticOddsBaseView):
    def get(self, request):
        try:
            return Response({"sports": OpticOddsClient().sports(), "demo": False})
        except OpticOddsError as exc:
            return Response({"sports": DEMO_SPORTS, "demo": True, "preview": True, "detail": str(exc)})


class AdminOpticOddsLeaguesView(OpticOddsBaseView):
    def get(self, request):
        try:
            return Response({"leagues": OpticOddsClient().leagues(request.query_params.get("sport")), "demo": False})
        except OpticOddsError as exc:
            return Response({"leagues": DEMO_LEAGUES.get(str(request.query_params.get("sport") or "").lower(), []), "demo": True, "preview": True, "detail": str(exc)})


class AdminOpticOddsFixturesView(OpticOddsBaseView):
    def get(self, request):
        if not request.query_params.get("sport") and not request.query_params.get("league"):
            return Response({"detail": "Pass a sport or league to load active fixtures."}, status=status.HTTP_400_BAD_REQUEST)
        live_only = request.query_params.get("live_only", "false").lower() == "true"
        start_after = request.query_params.get("start_date_after")
        if not start_after and not live_only:
            start_after = datetime.now(timezone.utc).isoformat()
        try:
            fixtures = OpticOddsClient().fixtures(
                sport=request.query_params.get("sport"),
                league=request.query_params.get("league"),
                live_only=live_only,
                start_date_after=start_after,
                start_date_before=request.query_params.get("start_date_before"),
            )
            return Response({"fixtures": fixtures, "filters": {"live_only": live_only, "start_date_after": start_after}, "demo": False})
        except OpticOddsError as exc:
            fixtures = [] if live_only else demo_fixtures(request.query_params.get("sport"), request.query_params.get("league"))
            return Response({"fixtures": fixtures, "filters": {"live_only": live_only, "start_date_after": start_after}, "demo": True, "preview": True, "detail": str(exc)})


class AdminOpticOddsFixtureOddsView(OpticOddsBaseView):
    def get(self, request, fixture_id):
        books = _books(request)
        try:
            market = request.query_params.get("market")
            rows = OpticOddsClient().odds(fixture_id, books, market=market)
            return Response({"fixture_id": fixture_id, "sportsbooks": books, "market": market, "odds": rows, "demo": False})
        except OpticOddsError as exc:
            market = request.query_params.get("market") or "moneyline"
            return Response({"fixture_id": fixture_id, "sportsbooks": books, "market": market, "odds": demo_odds(fixture_id, books, market), "demo": True, "preview": True, "detail": str(exc)})


def _demo_override_payload(item):
    return {
        "id": item.id,
        "fixture_id": item.fixture_id,
        "sportsbook": item.sportsbook,
        "market": item.market,
        "selection": item.selection,
        "decimal_odds": float(item.decimal_odds),
        "american_price": item.american_price,
        "active": item.active,
        "updated_at": item.updated_at,
    }


class AdminDemoOddsOverrideView(OpticOddsBaseView):
    """CRUD for admin demo price movements; live OpticOdds is never changed."""

    def get(self, request):
        queryset = DemoOddsOverride.objects.all()
        fixture_id = request.query_params.get("fixture_id")
        if fixture_id:
            queryset = queryset.filter(fixture_id=fixture_id)
        return Response({"overrides": [_demo_override_payload(item) for item in queryset], "demo_only": True})

    def post(self, request):
        data = request.data
        fixture_id = str(data.get("fixture_id") or "").strip()
        sportsbook = str(data.get("sportsbook") or "").strip().lower()
        market = str(data.get("market") or "moneyline").strip().lower()
        selection = str(data.get("selection") or "").strip()
        if not fixture_id or not sportsbook or not selection:
            return Response({"detail": "fixture_id, sportsbook and selection are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            decimal_value = Decimal(str(data.get("decimal_odds"))) if data.get("decimal_odds") not in (None, "") else None
        except (InvalidOperation, TypeError, ValueError):
            decimal_value = None
        try:
            american_value = int(float(data.get("american_price"))) if data.get("american_price") not in (None, "") else None
        except (TypeError, ValueError):
            american_value = None
        if decimal_value is None and american_value:
            decimal_value = Decimal(str(1 + american_value / 100 if american_value > 0 else 1 + 100 / abs(american_value)))
        if decimal_value is None or not decimal_value.is_finite() or decimal_value <= 1:
            return Response({"detail": "Enter valid decimal odds greater than 1.00 (or a non-zero American price)."}, status=status.HTTP_400_BAD_REQUEST)
        if american_value is None:
            american_value = round((float(decimal_value) - 1) * 100) if decimal_value >= 2 else round(-100 / (float(decimal_value) - 1))
        user = request.user if getattr(request.user, "is_authenticated", False) else None
        item, _ = DemoOddsOverride.objects.update_or_create(
            fixture_id=fixture_id,
            sportsbook=sportsbook,
            market=market,
            selection=selection,
            defaults={"decimal_odds": decimal_value, "american_price": american_value, "active": True, "updated_by": user},
        )
        return Response({"override": _demo_override_payload(item), "saved": True, "demo_only": True}, status=status.HTTP_200_OK)

    def delete(self, request):
        data = request.data or {}
        filters = {key: str(data.get(key) or "").strip() for key in ("fixture_id", "sportsbook", "market", "selection")}
        filters["sportsbook"] = filters["sportsbook"].lower()
        filters["market"] = filters["market"].lower()
        if not filters["fixture_id"] or not filters["sportsbook"] or not filters["selection"]:
            return Response({"detail": "fixture_id, sportsbook and selection are required."}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = DemoOddsOverride.objects.filter(**filters).delete()
        return Response({"deleted": deleted > 0, "demo_only": True})


class AdminOpticOddsBetMonitorView(OpticOddsBaseView):
    """Record a simulated admin sportsbook bet and its odds comparison."""

    def post(self, request):
        data = request.data
        required = ["fixture_id", "market", "selection"]
        missing = [key for key in required if not data.get(key)]
        if missing:
            return Response({"detail": f"Missing required fields: {', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)
        primary = str(data.get("sportsbook") or _primary_sportsbook()).lower()
        preference = saved_preference()
        configured = preference_payload(preference) if preference else None
        books = [configured["baseline"], *configured["selected_books"]] if configured else _books(request, data)
        if primary not in books:
            books.insert(0, primary)
        rows = list(data.get("odds_snapshot") or [])
        snapshot_books = {str(row.get("sportsbook", "")).lower() for row in rows if isinstance(row, dict)}
        if not rows or any(book not in snapshot_books for book in books):
            try:
                rows = OpticOddsClient().odds(str(data["fixture_id"]), books, market=str(data["market"]))
            except OpticOddsError:
                rows.extend(row for row in demo_odds(str(data["fixture_id"]), books, str(data["market"])) if row["sportsbook"] not in snapshot_books)
        if str(data["fixture_id"]).startswith("demo-"):
            rows = demo_odds(str(data["fixture_id"]), books, str(data["market"]))
        wanted_market = str(data["market"]).lower()
        wanted_selection = str(data["selection"]).lower()
        matching = [row for row in rows if str(row.get("market", "")).lower() == wanted_market and str(row.get("selection", "")).lower() == wanted_selection]
        if not matching:
            return Response({"detail": "The selected market/selection was not found for the requested fixture."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        weights = configured["provider_weights"] if configured else (data.get("provider_weights") or {})
        provider_odds, probability, fair_decimal = _weighted(matching, weights)
        primary_line = provider_odds.get(primary)
        if not primary_line:
            return Response({"detail": f"No {_primary_label()} price is available for this selection."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        peer_lines = {book: line["decimal"] for book, line in provider_odds.items() if book != primary}
        normalised_weights = _normalise_peer_weights(peer_lines, weights)
        peer_decimals = list(peer_lines.values())
        aggregate_comp_odds = sum(normalised_weights[book] * (1 / decimal) for book, decimal in peer_lines.items()) if peer_lines else None
        # The comparison probability is the weighted reciprocal of peer
        # prices. The baseline is used only for EV, never included in this
        # peer aggregate.
        probability = round(aggregate_comp_odds, 6) if aggregate_comp_odds is not None else None
        fair_decimal = round(1 / aggregate_comp_odds, 4) if aggregate_comp_odds else None
        ev_odds = (1 / primary_line["decimal"] - aggregate_comp_odds) if aggregate_comp_odds is not None else None
        try:
            ev_amount = round(float(data.get("stake")) * ev_odds, 2) if ev_odds is not None and data.get("stake") is not None else None
        except (TypeError, ValueError):
            ev_amount = None
        lowest_peer = min(peer_decimals) if peer_decimals else None
        highest_peer = max(peer_decimals) if peer_decimals else None
        edge_decimal = round(primary_line["decimal"] - lowest_peer, 4) if lowest_peer is not None else None
        relative_edge = edge_decimal / lowest_peer if edge_decimal is not None and lowest_peer else 0
        above_all = highest_peer is not None and primary_line["decimal"] > highest_peer
        significant = edge_decimal is not None and edge_decimal >= settings.OPTIC_ODDS_AUDIT_MIN_DECIMAL_GAP and relative_edge >= settings.OPTIC_ODDS_AUDIT_MIN_RELATIVE_GAP
        is_potentially_bad = bool(above_all or significant)
        audit_reason = "Higher than every selected provider" if above_all else ("Significantly above the lowest selected price" if significant else "Within the selected market range")
        event = data.get("event") or matching[0].get("event") or ""
        label = event or f"{data.get('selection')} {data.get('market')}"
        comparison = ", ".join(f"{book}: {values['decimal']:.2f}" for book, values in provider_odds.items() if book != primary) or "no peer quote available"
        weight_text = ", ".join(f"{book} {normalised_weights.get(book, 0):.2%}" for book in normalised_weights)
        formula = " + ".join(f"{book} {normalised_weights.get(book, 0):.2%} × 1/{values['decimal']:.2f}" for book, values in provider_odds.items() if book != primary)
        audit_note = f" | Audit: POTENTIALLY BAD — {audit_reason}" if is_potentially_bad else " | Audit: within selected market range"
        risk_margin_pct = (ev_odds * 100) if ev_odds is not None else None
        ev_note = f" | PRIME Risk Margin: {risk_margin_pct:+.2f}% · PRIME Risk Dollar Value: ${ev_amount:,.2f}" if risk_margin_pct is not None and ev_amount is not None else " | PRIME risk unavailable (no peer price)"
        probability_text = f"{probability:.2%}" if probability is not None else "—"
        aggregate_decimal_text = f"{fair_decimal:.2f}" if fair_decimal is not None else "—"
        note = f"{label} | {_primary_label()} {primary_line['decimal']:.2f} vs. {comparison} | BullBear Comp Price: {aggregate_decimal_text}{ev_note} | Weighted implied probability: {probability_text}{audit_note}"
        # Service-key calls authenticate the application, not an individual
        # Django user. AnonymousUser cannot be assigned to a User FK, so keep
        # admin_user NULL for those records; JWT-authenticated admin calls keep
        # their actor identity.
        admin_user = request.user if getattr(request.user, "is_authenticated", False) else None
        record = OpticOddsBetMonitor.objects.create(
            admin_user=admin_user,
            fixture_id=str(data["fixture_id"]), event=str(event),
            sport=str(data.get("sport", "")), league=str(data.get("league", "")),
            market=str(data["market"]), selection=str(data["selection"]),
            primary_sportsbook=primary, primary_price=str(primary_line.get("price", "")),
            primary_decimal=primary_line.get("decimal"), stake=data.get("stake"),
            provider_odds=provider_odds, provider_weights=normalised_weights, aggregate_comp_odds=aggregate_comp_odds, ev_odds=ev_odds, ev_amount=ev_amount,
            weighted_implied_probability=probability, fair_decimal=fair_decimal,
            is_potentially_bad=is_potentially_bad, audit_reason=audit_reason, edge_decimal=edge_decimal,
            note=note, odds_snapshot=matching,
        )
        return Response({"id": record.id, "created_at": record.created_at, "patron_id": admin_user.id if admin_user else None, "patron_username": admin_user.username if admin_user else None, "note": note, "primary": primary_line, "primary_sportsbook": primary, "primary_sportsbook_label": _primary_label(), "provider_odds": provider_odds, "provider_weights": normalised_weights, "weighted_implied_probability": probability, "fair_decimal": fair_decimal, "aggregate_comp_odds": aggregate_comp_odds, "aggregate_comp_decimal_odds": (round(1 / aggregate_comp_odds, 4) if aggregate_comp_odds else None), "ev_odds": ev_odds, "ev_amount": ev_amount, **_risk_fields(ev_odds, ev_amount), "formula": formula, "is_potentially_bad": is_potentially_bad, "audit_reason": audit_reason, "edge_decimal": edge_decimal, "edge_percent": (round((edge_decimal / lowest_peer) * 100, 4) if edge_decimal is not None and lowest_peer else None)}, status=status.HTTP_201_CREATED)


def _monitor_payload(row):
    """Serialize one monitor leg with patron and CEO-facing risk terminology."""
    slip = row.sportsbook_slip
    # The patron is the account that owns the recorded betslip. ``admin_user``
    # is the user who submitted the admin-only comparison endpoint and can be
    # a staff account; prefer the betslip owner whenever one is linked.
    patron = (slip.user if slip else None) or row.admin_user
    provider_odds = row.provider_odds or {}
    primary = str(row.primary_sportsbook or _primary_sportsbook()).strip().lower()
    peer_decimals = [
        float(line.get("decimal"))
        for book, line in provider_odds.items()
        if book != primary and isinstance(line, dict) and line.get("decimal") not in (None, "")
    ]
    edge_percent = None
    if row.edge_decimal is not None and peer_decimals and min(peer_decimals) > 0:
        edge_percent = round(float(row.edge_decimal) / min(peer_decimals) * 100, 4)
    risk = _risk_fields(row.ev_odds, row.ev_amount)
    slip_risk = _risk_fields(slip.ev_odds, slip.ev_amount) if slip else _risk_fields(None, None)
    return {
        "id": row.id,
        "created_at": row.created_at,
        "fixture_id": row.fixture_id,
        "event": row.event,
        "sport": row.sport,
        "league": row.league,
        "market": row.market,
        "selection": row.selection,
        "patron_id": patron.id if patron else None,
        "patron_username": patron.username if patron else None,
        "primary_sportsbook": primary,
        "primary_sportsbook_label": _primary_label(),
        "primary_decimal": row.primary_decimal,
        "provider_odds": provider_odds,
        "provider_weights": row.provider_weights,
        "weighted_implied_probability": row.weighted_implied_probability,
        "fair_decimal": row.fair_decimal,
        "aggregate_comp_odds": row.aggregate_comp_odds,
        "aggregate_comp_decimal_odds": (round(1 / row.aggregate_comp_odds, 4) if row.aggregate_comp_odds else None),
        "ev_odds": row.ev_odds,
        "ev_amount": str(row.ev_amount) if row.ev_amount is not None else None,
        **risk,
        "slip_id": row.sportsbook_slip_id,
        "slip_stake": str(slip.stake) if slip else None,
        "slip_combined_decimal_odds": float(slip.combined_decimal_odds) if slip else None,
        "slip_aggregate_comp_odds": slip.aggregate_comp_odds if slip else None,
        "slip_aggregate_comp_decimal_odds": (round(1 / slip.aggregate_comp_odds, 4) if slip and slip.aggregate_comp_odds else None),
        "slip_potential_payout": str(slip.potential_payout) if slip else None,
        "slip_leg_count": slip.leg_count if slip else 1,
        "slip_ev_odds": slip.ev_odds if slip else None,
        "slip_ev_amount": str(slip.ev_amount) if slip and slip.ev_amount is not None else None,
        "slip_prime_risk_margin": slip_risk["prime_risk_margin"],
        "slip_prime_risk_dollar_value": slip_risk["prime_risk_dollar_value"],
        "is_potentially_bad": row.is_potentially_bad,
        "audit_reason": row.audit_reason,
        "insight": {"message": row.audit_reason, "source": "rule_based", "review_required": row.is_potentially_bad},
        "edge_decimal": row.edge_decimal,
        "edge_percent": edge_percent,
        "edge_methodology": EDGE_METHODOLOGY,
        "note": row.note,
    }


class AdminOpticOddsBetMonitorListView(OpticOddsBaseView):
    def get(self, request):
        try:
            page = max(int(request.query_params.get("page", 1)), 1)
            page_size = min(max(int(request.query_params.get("page_size", 20)), 1), 100)
        except (TypeError, ValueError):
            page, page_size = 1, 20
        # Do not rely on database/default-manager ordering here. New records
        # must always appear first in the monitoring feed, even when several
        # bets share the same timestamp precision.
        queryset = OpticOddsBetMonitor.objects.select_related("admin_user", "sportsbook_slip", "sportsbook_slip__user").order_by("-created_at", "-id")
        query = str(request.query_params.get("q", "")).strip()
        status_filter = str(request.query_params.get("status", "all")).lower()
        sport = str(request.query_params.get("sport", "")).strip()
        league = str(request.query_params.get("league", "")).strip()
        patron_id = str(request.query_params.get("patron_id", "")).strip()
        patron_username = str(request.query_params.get("patron_username", "")).strip()
        if query:
            queryset = queryset.filter(Q(event__icontains=query) | Q(selection__icontains=query) | Q(market__icontains=query) | Q(fixture_id__icontains=query))
        if status_filter == "flagged":
            queryset = queryset.filter(is_potentially_bad=True)
        elif status_filter in {"clear", "within_range"}:
            queryset = queryset.filter(is_potentially_bad=False)
        if sport:
            queryset = queryset.filter(sport__iexact=sport)
        if league:
            queryset = queryset.filter(league__iexact=league)
        if patron_id:
            try:
                patron_pk = int(patron_id)
                queryset = queryset.filter(Q(admin_user_id=patron_pk) | Q(sportsbook_slip__user_id=patron_pk))
            except ValueError:
                queryset = queryset.none()
        if patron_username:
            queryset = queryset.filter(Q(admin_user__username__iexact=patron_username) | Q(sportsbook_slip__user__username__iexact=patron_username))
        flagged_total = queryset.filter(is_potentially_bad=True).count()
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        records = page_obj.object_list
        return Response({"bets": [_monitor_payload(row) for row in records], "primary_sportsbook": _primary_sportsbook(), "primary_sportsbook_label": _primary_label(), "edge_methodology": EDGE_METHODOLOGY, "pagination": {"page": page_obj.number, "page_size": page_size, "total": paginator.count, "flagged_total": flagged_total, "pages": paginator.num_pages, "has_next": page_obj.has_next(), "has_previous": page_obj.has_previous()}})


class AdminOpticOddsPatronNotesView(OpticOddsBaseView):
    """Return one patron's complete sportsbook note history and risk totals."""

    def get(self, request, user_id):
        try:
            patron = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Patron profile not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            page = max(int(request.query_params.get("page", 1)), 1)
            page_size = min(max(int(request.query_params.get("page_size", 20)), 1), 100)
        except (TypeError, ValueError):
            page, page_size = 1, 20

        slips = SportsbookBetSlip.objects.filter(user=patron).order_by("-created_at", "-id")
        evaluated = slips.filter(ev_amount__isnull=False)
        totals = evaluated.aggregate(total_stake=Sum("stake"), total_ev=Sum("ev_amount"))
        total_stake = totals["total_stake"] or Decimal("0")
        total_ev = totals["total_ev"] or Decimal("0")
        prime_edge = (total_ev / total_stake * Decimal("100")) if total_stake else None
        paginator = Paginator(slips, page_size)
        page_obj = paginator.get_page(page)

        notes = []
        for slip in page_obj.object_list:
            risk = _risk_fields(slip.ev_odds, slip.ev_amount)
            notes.append({
                "slip_id": slip.id,
                "created_at": slip.created_at,
                "stake": str(slip.stake),
                "combined_decimal_odds": float(slip.combined_decimal_odds),
                "potential_payout": str(slip.potential_payout),
                "leg_count": slip.leg_count,
                "primary_sportsbook": _primary_sportsbook(),
                "primary_sportsbook_label": _primary_label(),
                "aggregate_comp_odds": slip.aggregate_comp_odds,
                "aggregate_comp_decimal_odds": (round(1 / slip.aggregate_comp_odds, 4) if slip.aggregate_comp_odds else None),
                "ev_odds": slip.ev_odds,
                "ev_amount": str(slip.ev_amount) if slip.ev_amount is not None else None,
                **risk,
                "comparison_notes": slip.comparison_notes or [],
                "legs": slip.legs or [],
                "status": slip.status,
            })
        return Response({
            "patron": {"id": patron.id, "username": patron.username},
            "summary": {
                "prime_edge": round(float(prime_edge), 4) if prime_edge is not None else None,
                "prime_edge_percent": round(float(prime_edge), 4) if prime_edge is not None else None,
                "prime_exposure": str(total_ev),
                "total_stake": str(total_stake),
                "evaluated_wagers": evaluated.count(),
                "total_wagers": slips.count(),
                "edge_methodology": EDGE_METHODOLOGY,
            },
            "notes": notes,
            "primary_sportsbook": _primary_sportsbook(),
            "primary_sportsbook_label": _primary_label(),
            "pagination": {"page": page_obj.number, "page_size": page_size, "total": paginator.count, "pages": paginator.num_pages, "has_next": page_obj.has_next(), "has_previous": page_obj.has_previous()},
        })
