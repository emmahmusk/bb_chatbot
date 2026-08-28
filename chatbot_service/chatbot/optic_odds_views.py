from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.optic_odds import OpticOddsError, catalog, compare_odds, sportsbooks


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
