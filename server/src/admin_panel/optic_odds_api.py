from __future__ import annotations

import logging
from datetime import datetime, timezone

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_panel.models import OpticOddsBetMonitor
from admin_panel.optic_odds import OpticOddsClient, OpticOddsError, default_sportsbooks
from admin_panel.permissions import IsAdminOrServiceKey

logger = logging.getLogger(__name__)


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
            return Response({"sports": OpticOddsClient().sports()})
        except OpticOddsError as exc:
            return _error(exc)


class AdminOpticOddsLeaguesView(OpticOddsBaseView):
    def get(self, request):
        try:
            return Response({"leagues": OpticOddsClient().leagues(request.query_params.get("sport"))})
        except OpticOddsError as exc:
            return _error(exc)


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
            return Response({"fixtures": fixtures, "filters": {"live_only": live_only, "start_date_after": start_after}})
        except OpticOddsError as exc:
            return _error(exc)


class AdminOpticOddsFixtureOddsView(OpticOddsBaseView):
    def get(self, request, fixture_id):
        books = _books(request)
        try:
            market = request.query_params.get("market")
            rows = OpticOddsClient().odds(fixture_id, books, market=market)
            return Response({"fixture_id": fixture_id, "sportsbooks": books, "market": market, "odds": rows})
        except OpticOddsError as exc:
            return _error(exc)


class AdminOpticOddsBetMonitorView(OpticOddsBaseView):
    """Record a simulated admin sportsbook bet and its odds comparison."""

    def post(self, request):
        data = request.data
        required = ["fixture_id", "market", "selection"]
        missing = [key for key in required if not data.get(key)]
        if missing:
            return Response({"detail": f"Missing required fields: {', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)
        primary = str(data.get("sportsbook") or settings.OPTIC_ODDS_PRIMARY_SPORTSBOOK).lower()
        books = _books(request, data)
        if primary not in books:
            books.insert(0, primary)
        try:
            rows = data.get("odds_snapshot") or OpticOddsClient().odds(str(data["fixture_id"]), books, market=str(data["market"]))
        except OpticOddsError as exc:
            return _error(exc)
        wanted_market = str(data["market"]).lower()
        wanted_selection = str(data["selection"]).lower()
        matching = [row for row in rows if str(row.get("market", "")).lower() == wanted_market and str(row.get("selection", "")).lower() == wanted_selection]
        if not matching:
            return Response({"detail": "The selected market/selection was not found for the requested fixture."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        weights = data.get("provider_weights") or {}
        provider_odds, probability, fair_decimal = _weighted(matching, weights)
        primary_line = provider_odds.get(primary)
        if not primary_line:
            return Response({"detail": f"No {primary} price is available for this selection."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        peer_decimals = [line["decimal"] for book, line in provider_odds.items() if book != primary]
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
        comparison = ", ".join(f"{book}: {values['decimal']:.2f}" for book, values in provider_odds.items())
        weight_text = ", ".join(f"{book} {float(weights.get(book, 1 / len(provider_odds))):.2g}" for book in provider_odds)
        formula = " + ".join(f"{book} {float(weights.get(book, 1 / len(provider_odds))):.2g} × 1/{values['decimal']:.2f}" for book, values in provider_odds.items())
        audit_note = f" | Audit: POTENTIALLY BAD — {audit_reason}" if is_potentially_bad else " | Audit: within selected market range"
        note = f"{label} | {primary_line['decimal']:.2f} vs. {comparison} | Weighted implied probability: {probability:.2%}{audit_note}"
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
            provider_odds=provider_odds, provider_weights=weights,
            weighted_implied_probability=probability, fair_decimal=fair_decimal,
            is_potentially_bad=is_potentially_bad, audit_reason=audit_reason, edge_decimal=edge_decimal,
            note=note, odds_snapshot=matching,
        )
        return Response({"id": record.id, "created_at": record.created_at, "note": note, "primary": primary_line, "provider_odds": provider_odds, "provider_weights": weights, "weighted_implied_probability": probability, "fair_decimal": fair_decimal, "formula": formula, "is_potentially_bad": is_potentially_bad, "audit_reason": audit_reason, "edge_decimal": edge_decimal}, status=status.HTTP_201_CREATED)


class AdminOpticOddsBetMonitorListView(OpticOddsBaseView):
    def get(self, request):
        try:
            page = max(int(request.query_params.get("page", 1)), 1)
            page_size = min(max(int(request.query_params.get("page_size", 20)), 1), 100)
        except (TypeError, ValueError):
            page, page_size = 1, 20
        queryset = OpticOddsBetMonitor.objects.select_related("admin_user").all()
        query = str(request.query_params.get("q", "")).strip()
        status_filter = str(request.query_params.get("status", "all")).lower()
        sport = str(request.query_params.get("sport", "")).strip()
        league = str(request.query_params.get("league", "")).strip()
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
        flagged_total = queryset.filter(is_potentially_bad=True).count()
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        records = page_obj.object_list
        return Response({"bets": [{"id": row.id, "created_at": row.created_at, "fixture_id": row.fixture_id, "event": row.event, "sport": row.sport, "league": row.league, "market": row.market, "selection": row.selection, "primary_sportsbook": row.primary_sportsbook, "primary_decimal": row.primary_decimal, "provider_odds": row.provider_odds, "provider_weights": row.provider_weights, "weighted_implied_probability": row.weighted_implied_probability, "fair_decimal": row.fair_decimal, "is_potentially_bad": row.is_potentially_bad, "audit_reason": row.audit_reason, "edge_decimal": row.edge_decimal, "note": row.note} for row in records], "pagination": {"page": page_obj.number, "page_size": page_size, "total": paginator.count, "flagged_total": flagged_total, "pages": paginator.num_pages, "has_next": page_obj.has_next(), "has_previous": page_obj.has_previous()}})
