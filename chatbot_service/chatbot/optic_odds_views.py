from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.optic_odds import OpticOddsError, catalog, compare_odds, sportsbooks
from .models import BetAudit


def _number(value):
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _audit_payload(audit):
    return {
        "id": audit.id,
        "fixture_id": audit.fixture_id,
        "sport": audit.sport,
        "league": audit.league,
        "market": audit.market,
        "selection": audit.selection,
        "chosen_sportsbook": audit.chosen_sportsbook,
        "chosen_price": audit.chosen_price,
        "chosen_decimal": audit.chosen_decimal,
        "best_sportsbook": audit.best_sportsbook,
        "best_price": audit.best_price,
        "best_decimal": audit.best_decimal,
        "edge_decimal": audit.edge_decimal,
        "is_bad_bet": audit.is_bad_bet,
        "comparison_snapshot": audit.comparison_snapshot,
        "created_at": audit.created_at.isoformat(),
    }


class OpticCatalogView(APIView):
    def get(self, request):
        sport = str(request.query_params.get("sport") or "basketball").strip()
        league = str(request.query_params.get("league") or "").strip()
        bootstrap = request.query_params.get("bootstrap") == "1"
        try:
            data, preview = catalog(sport=sport, league=league or None, bootstrap=bootstrap)
        except OpticOddsError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({**data, "preview": preview, "provider": "OpticOdds"})


class OpticSportsbooksView(APIView):
    def get(self, request):
        try:
            books, preview = sportsbooks()
        except OpticOddsError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"providers": books, "preview": preview, "provider": "OpticOdds"})


class OpticOddsCompareView(APIView):
    def post(self, request):
        selected_books = request.data.get("sportsbooks") or []
        if not isinstance(selected_books, list) or not 2 <= len(selected_books) <= 5:
            return Response(
                {"error": "Choose between 2 and 5 market providers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fixture_id = str(request.data.get("fixture_id") or "").strip()
        sport = str(request.data.get("sport") or "basketball").strip()
        league = str(request.data.get("league") or "").strip()
        market = str(request.data.get("market") or "moneyline").strip()
        if not fixture_id:
            fixture_id = None
        from django.conf import settings
        if getattr(settings, "OPTIC_ODDS_API_KEY", "") and not fixture_id:
            return Response(
                {"error": "Enter an OpticOdds fixture ID to compare live prices."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rows, preview = compare_odds(
                fixture_id=fixture_id,
                sport=sport,
                league=league,
                market=market,
                selected_books=[str(book).strip() for book in selected_books],
            )
        except OpticOddsError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({
            "provider": "OpticOdds",
            "preview": preview,
            "fixture_id": fixture_id,
            "sport": sport,
            "league": league,
            "market": market,
            "count": len(rows),
            "rows": rows,
        })


class BetAuditView(APIView):
    def get(self, request):
        return Response({"audits": [_audit_payload(item) for item in BetAudit.objects.all()[:50]]})

    def post(self, request):
        selected = request.data.get("selected_row") or {}
        rows = request.data.get("rows") or []
        if not isinstance(selected, dict) or not selected.get("sportsbook"):
            return Response({"error": "Select a sportsbook price to audit."}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(rows, list):
            return Response({"error": "Comparison rows are required for an audit."}, status=status.HTTP_400_BAD_REQUEST)
        chosen_decimal = _number(selected.get("decimal"))
        peers = [row for row in rows if isinstance(row, dict) and row.get("sportsbook") != selected.get("sportsbook") and row.get("selection") == selected.get("selection") and row.get("event") == selected.get("event") and row.get("market") == selected.get("market") and _number(row.get("decimal")) is not None]
        best = max(peers, key=lambda row: _number(row.get("decimal")), default=None)
        best_decimal = _number(best.get("decimal")) if best else None
        edge = round(best_decimal - chosen_decimal, 4) if chosen_decimal is not None and best_decimal is not None else None
        is_bad = bool(edge is not None and edge > 0.0001)
        audit = BetAudit.objects.create(
            fixture_id=str(selected.get("fixture_id") or ""),
            sport=str(request.data.get("sport") or ""),
            league=str(request.data.get("league") or ""),
            market=str(selected.get("market") or request.data.get("market") or ""),
            selection=str(selected.get("selection") or ""),
            chosen_sportsbook=str(selected.get("sportsbook") or ""),
            chosen_price=_number(selected.get("price")),
            chosen_decimal=chosen_decimal,
            best_sportsbook=str(best.get("sportsbook") or "") if best else "",
            best_price=_number(best.get("price")) if best else None,
            best_decimal=best_decimal,
            edge_decimal=edge,
            is_bad_bet=is_bad,
            comparison_snapshot=rows,
        )
        return Response(_audit_payload(audit), status=status.HTTP_201_CREATED)
