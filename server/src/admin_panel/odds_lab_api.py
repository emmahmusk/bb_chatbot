"""Admin odds settings and a demo-only catalog with no provider dependency."""
import math
import re
from django.core.cache import cache
from rest_framework.response import Response
from admin_panel.models import SportsbookComparisonSettings
from admin_panel.odds_preferences import baseline, normalize_weights, preference_payload, saved_preference
from admin_panel.optic_odds import OpticOddsClient, OpticOddsError, DEMO_SPORTS, DEMO_LEAGUES, demo_fixtures, demo_odds, _canonical_sportsbook
from admin_panel.optic_odds_api import OpticOddsBaseView


class AdminComparisonSettingsView(OpticOddsBaseView):
    def get(self, request):
        return Response(preference_payload(saved_preference()))

    def post(self, request):
        raw = request.data.get("selected_books")
        if not isinstance(raw, list) or any(not isinstance(book, str) for book in raw):
            return Response({"detail": "selected_books must be a list of provider IDs."}, status=400)
        books = list(dict.fromkeys(book.strip().lower() for book in raw if book.strip() and book.strip().lower() != baseline()))
        if not 1 <= len(books) <= 4 or any(not re.fullmatch(r"[a-z0-9_-]{1,80}", book) for book in books):
            return Response({"detail": "Select between one and four valid peer books."}, status=400)
        supplied = request.data.get("provider_weights")
        if not isinstance(supplied, dict):
            return Response({"detail": "provider_weights must contain a weight for each selected book."}, status=400)
        try:
            values = [float(supplied.get(book, 0)) for book in books]
        except (TypeError, ValueError):
            values = []
        if not values or any(not math.isfinite(value) or value < 0 for value in values) or sum(values) <= 0:
            return Response({"detail": "Enter non-negative finite weights with a positive total."}, status=400)
        preference, _ = SportsbookComparisonSettings.objects.update_or_create(pk=1, defaults={
            "selected_books": books, "provider_weights": normalize_weights(books, supplied),
        })
        return Response({**preference_payload(preference), "saved": True})


class AdminComparisonProvidersView(OpticOddsBaseView):
    def get(self, request):
        labels = {"draftkings": "DraftKings", "fanduel": "FanDuel", "pinnacle": "Pinnacle", "bet365": "bet365", "betmgm": "BetMGM", "caesars": "Caesars", "hardrockbet": "Hard Rock"}
        providers = cache.get("admin-odds-provider-catalog")
        preview = False
        if providers is None:
            try:
                body = OpticOddsClient()._get("sportsbooks")
                rows = body if isinstance(body, list) else body.get("data", body.get("sportsbooks", []))
                if isinstance(rows, dict):
                    rows = rows.get("sportsbooks", [])
                providers = [{"id": _canonical_sportsbook(row), "name": row.get("name") or row.get("id")} for row in rows if isinstance(row, dict) and row.get("is_active", True)]
                providers = [provider for provider in providers if provider["id"]]
                cache.set("admin-odds-provider-catalog", providers, 300)
            except OpticOddsError:
                providers, preview = [], True
        preference = preference_payload(saved_preference())
        merged = {provider["id"]: provider for provider in providers}
        fallback = list(labels) if not providers else []
        for book in [preference["baseline"], *preference["selected_books"], *fallback]:
            merged.setdefault(book, {"id": book, "name": labels.get(book, book)})
        return Response({"providers": list(merged.values()), "preview": preview, "primary_sportsbook": preference["baseline"], "primary_sportsbook_label": preference["baseline_label"]})


class AdminDemoLabSportsView(OpticOddsBaseView):
    def get(self, request):
        return Response({"sports": DEMO_SPORTS, "demo": True})


class AdminDemoLabLeaguesView(OpticOddsBaseView):
    def get(self, request):
        return Response({"leagues": DEMO_LEAGUES.get(str(request.query_params.get("sport", "soccer")).lower(), []), "demo": True})


class AdminDemoLabFixturesView(OpticOddsBaseView):
    def get(self, request):
        return Response({"fixtures": demo_fixtures(request.query_params.get("sport"), request.query_params.get("league")), "demo": True})


class AdminDemoLabOddsView(OpticOddsBaseView):
    def get(self, request, fixture_id):
        if not re.fullmatch(r"demo-(?:soccer|basketball|baseball|football|hockey|tennis)-00[1-5]", fixture_id):
            return Response({"detail": "Choose a generated demo fixture."}, status=400)
        market = request.query_params.get("market", "moneyline")
        if market not in {"moneyline", "point_spread", "total_points", "run_line", "total_runs"}:
            return Response({"detail": "Unknown demo market."}, status=400)
        books = list(dict.fromkeys(book.strip().lower() for book in request.query_params.get("sportsbooks", "draftkings,fanduel,pinnacle,bet365").split(",") if book.strip()))[:5]
        return Response({"fixture_id": fixture_id, "market": market, "odds": demo_odds(fixture_id, books, market), "demo": True})
