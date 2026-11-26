"""One-time import from the legacy chatbot SQLite database, opened read-only."""
import json
import sqlite3
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from admin_panel.models import DemoOddsOverride, SportsbookComparisonSettings
from admin_panel.odds_preferences import normalize_weights


class Command(BaseCommand):
    help = "Import legacy chatbot monitor settings/demo overrides without modifying the source SQLite database."

    def add_arguments(self, parser):
        parser.add_argument("database", type=Path)
        parser.add_argument("--replace", action="store_true", help="Replace conflicting server values; otherwise preserve them.")

    @transaction.atomic
    def handle(self, database, **options):
        source = database.resolve()
        if not source.is_file():
            raise CommandError("The source chatbot database does not exist.")
        try:
            connection = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            preferences = connection.execute("SELECT selected_books, provider_weights FROM chatbot_sportsbookpreference WHERE id=1").fetchone()
            overrides = connection.execute("SELECT fixture_id, sportsbook, market, selection, decimal_odds, american_price, active FROM chatbot_demooddslaboverride").fetchall()
        except sqlite3.Error as exc:
            raise CommandError(f"Unable to read legacy odds tables: {exc}") from exc
        finally:
            if "connection" in locals():
                connection.close()
        if preferences:
            books = json.loads(preferences["selected_books"])
            defaults = {"selected_books": books, "provider_weights": normalize_weights(books, json.loads(preferences["provider_weights"]))}
            method = SportsbookComparisonSettings.objects.update_or_create if options["replace"] else SportsbookComparisonSettings.objects.get_or_create
            method(pk=1, defaults=defaults)
        imported = 0
        for row in overrides:
            identity = {field: row[field] for field in ("fixture_id", "sportsbook", "market", "selection")}
            defaults = {field: row[field] for field in ("decimal_odds", "american_price", "active")}
            method = DemoOddsOverride.objects.update_or_create if options["replace"] else DemoOddsOverride.objects.get_or_create
            _, created = method(**identity, defaults=defaults)
            imported += int(created)
        self.stdout.write(self.style.SUCCESS(f"Imported settings and {imported} new demo overrides. Source database unchanged."))
