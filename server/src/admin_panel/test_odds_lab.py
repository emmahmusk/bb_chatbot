import io
import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from admin_panel.models import DemoOddsOverride, OpticOddsBetMonitor, SportsbookComparisonSettings
from admin_panel.optic_odds import demo_odds, OpticOddsError
from admin_panel.odds_preferences import preference_payload, saved_preference


class OddsLabIntegrationTests(TestCase):
    prefix = "/admin_panel/optic-odds/"

    def setUp(self):
        cache.clear()
        self.admin = get_user_model().objects.create_user(username="odds_admin", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def save_settings(self):
        response = self.client.post(self.prefix + "settings/", {
            "selected_books": ["fanduel", "pinnacle"],
            "provider_weights": {"fanduel": 25, "pinnacle": 75},
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response

    def test_admin_permissions_and_real_jwt(self):
        anonymous = APIClient()
        for route in ["settings/", "providers/", "demo-lab/sports/", "demo-lab/leagues/", "demo-lab/fixtures/", "demo-lab/fixtures/demo-soccer-001/odds/", "demo-odds/", "bets/monitor/"]:
            self.assertEqual(anonymous.get(self.prefix + route).status_code, 401, route)
        ordinary = get_user_model().objects.create_user(username="ordinary")
        anonymous.force_authenticate(ordinary)
        self.assertEqual(anonymous.get(self.prefix + "settings/").status_code, 403)
        jwt_client = APIClient()
        jwt_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.admin).access_token}")
        self.assertEqual(jwt_client.get(self.prefix + "settings/").status_code, 200)

    def test_settings_persist_normalize_and_exclude_baseline(self):
        response = self.save_settings()
        self.assertEqual(response.data["provider_weights"], {"fanduel": .25, "pinnacle": .75})
        self.assertEqual(preference_payload(saved_preference())["selected_books"], ["fanduel", "pinnacle"])
        self.assertEqual(self.client.get(self.prefix + "settings/").data["provider_weights"], response.data["provider_weights"])
        response = self.client.post(self.prefix + "settings/", {"selected_books": ["draftkings", "fanduel"], "provider_weights": {"fanduel": 1}}, format="json")
        self.assertEqual(response.data["selected_books"], ["fanduel"])

    def test_invalid_settings_do_not_replace_saved_values(self):
        self.save_settings()
        for data in [
            {"selected_books": [], "provider_weights": {}},
            {"selected_books": ["a", "b", "c", "d", "e"], "provider_weights": {"a": 1}},
            {"selected_books": ["fanduel"], "provider_weights": {"fanduel": "NaN"}},
            {"selected_books": ["fanduel"], "provider_weights": {"fanduel": -1}},
            {"selected_books": ["fanduel"], "provider_weights": {"fanduel": 0}},
        ]:
            self.assertEqual(self.client.post(self.prefix + "settings/", data, format="json").status_code, 400)
        self.assertEqual(saved_preference().selected_books, ["fanduel", "pinnacle"])

    @patch("admin_panel.optic_odds.OpticOddsClient._get", side_effect=AssertionError("Demo lab called provider"))
    def test_complete_demo_flow_never_calls_opticodds(self, upstream):
        self.assertEqual(len(self.client.get(self.prefix + "demo-lab/sports/").data["sports"]), 6)
        self.assertTrue(self.client.get(self.prefix + "demo-lab/leagues/", {"sport": "soccer"}).data["leagues"])
        fixture = self.client.get(self.prefix + "demo-lab/fixtures/", {"sport": "soccer"}).data["fixtures"][0]
        path = self.prefix + f"demo-lab/fixtures/{fixture['fixture_id']}/odds/"
        before = self.client.get(path).data["odds"][0]
        identity = {"fixture_id": fixture["fixture_id"], "sportsbook": before["sportsbook"], "market": "moneyline", "selection": before["selection"]}
        response = self.client.post(self.prefix + "demo-odds/", {**identity, "decimal_odds": 2.7}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.get(path).data["odds"][0]["decimal"], 2.7)
        other_market = self.client.get(path, {"market": "total_runs"}).data["odds"][0]
        self.assertNotEqual(other_market["decimal"], 2.7)
        self.assertEqual(len(self.client.get(self.prefix + "demo-odds/", {"fixture_id": fixture["fixture_id"]}).data["overrides"]), 1)
        self.assertTrue(self.client.delete(self.prefix + "demo-odds/", identity, format="json").data["deleted"])
        self.assertEqual(self.client.get(path).data["odds"][0]["decimal"], before["decimal"])
        upstream.assert_not_called()

    def test_provider_catalog_survives_missing_key(self):
        response = self.client.get(self.prefix + "providers/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("fanduel", [book["id"] for book in response.data["providers"]])

    def test_saved_preferences_and_override_reach_recorded_slip_and_monitor(self):
        self.save_settings()
        rows = demo_odds("demo-soccer-001", ["draftkings"], "moneyline")
        identity = {"fixture_id": "demo-soccer-001", "sportsbook": "draftkings", "market": "moneyline", "selection": rows[0]["selection"]}
        self.client.post(self.prefix + "demo-odds/", {**identity, "decimal_odds": 2.9}, format="json")
        response = self.client.post("/bet/sportsbook/betslips/", {
            "stake": "100", "demo": True,
            "sportsbooks": ["draftkings", "caesars"], "provider_weights": {"caesars": 1},
            "legs": [{"fixture_id": "demo-soccer-001", "market": "moneyline", "selection": rows[0]["selection"], "odds_snapshot": [rows[0]]}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        record = OpticOddsBetMonitor.objects.get()
        self.assertEqual(record.primary_decimal, 2.9)
        self.assertEqual(record.provider_weights, {"fanduel": .25, "pinnacle": .75})
        self.assertNotIn("caesars", record.provider_odds)
        feed = self.client.get(self.prefix + "bets/monitor/", {"q": rows[0]["selection"], "status": "flagged"})
        self.assertEqual(feed.data["pagination"]["total"], 1)
        self.assertEqual(feed.data["bets"][0]["slip_id"], response.data["slip_id"])
        self.assertIn("slip_prime_risk_margin", feed.data["bets"][0])

    def test_admin_simulation_uses_shared_weights(self):
        self.save_settings()
        rows = demo_odds("demo-soccer-001", ["draftkings", "fanduel", "pinnacle"], "moneyline")
        response = self.client.post(self.prefix + "bets/", {
            "fixture_id": "demo-soccer-001", "market": "moneyline", "selection": rows[0]["selection"],
            "stake": 50, "odds_snapshot": rows,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(OpticOddsBetMonitor.objects.get().provider_weights, {"fanduel": .25, "pinnacle": .75})

    def test_legacy_import_is_idempotent_and_preserves_server_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "chatbot.sqlite3"
            with sqlite3.connect(source) as connection:
                connection.execute("CREATE TABLE chatbot_sportsbookpreference (id integer, selected_books text, provider_weights text)")
                connection.execute("INSERT INTO chatbot_sportsbookpreference VALUES (1, ?, ?)", (json.dumps(["fanduel"]), json.dumps({"fanduel": 1})))
                connection.execute("CREATE TABLE chatbot_demooddslaboverride (fixture_id text, sportsbook text, market text, selection text, decimal_odds real, american_price integer, active integer)")
                connection.execute("INSERT INTO chatbot_demooddslaboverride VALUES ('demo-soccer-001', 'fanduel', 'moneyline', 'Arsenal FC', 2.2, 120, 1)")
            connection.close()
            before = source.read_bytes()
            for _ in range(2):
                call_command("import_chatbot_odds_lab", source, stdout=io.StringIO())
            self.assertEqual(DemoOddsOverride.objects.count(), 1)
            self.assertEqual(SportsbookComparisonSettings.objects.count(), 1)
            self.assertEqual(source.read_bytes(), before)
            self.save_settings()
            call_command("import_chatbot_odds_lab", source, stdout=io.StringIO())
            self.assertEqual(saved_preference().selected_books, ["fanduel", "pinnacle"])
