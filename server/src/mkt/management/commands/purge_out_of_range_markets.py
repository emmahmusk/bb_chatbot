from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from betengine.models import (
    Market,
    PROBABILITY_GUARDRAIL_CEILING,
    PROBABILITY_GUARDRAIL_FLOOR,
)


class Command(BaseCommand):
    help = (
        "Deactivate markets whose current implied probabilities fall outside the "
        "platform 20%-80% guardrail. Optionally hard-delete invalid inactive "
        "markets that have no related bets."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbols",
            nargs="+",
            help="Optional stock symbols to scope the cleanup to, e.g. AAPL TSLA NVDA",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview affected markets without changing the database.",
        )
        parser.add_argument(
            "--hard-delete-inactive-orphans",
            action="store_true",
            help=(
                "Also hard-delete invalid inactive markets that have no related bets. "
                "Active invalid markets are always deactivated first."
            ),
        )

    def handle(self, *args, **options):
        normalized_symbols = sorted(
            {
                symbol.strip().upper()
                for symbol in (options.get("symbols") or [])
                if isinstance(symbol, str) and symbol.strip()
            }
        )
        dry_run = options["dry_run"]
        hard_delete_orphans = options["hard_delete_inactive_orphans"]

        invalid_filter = (
            Q(implied_odds_over__lt=PROBABILITY_GUARDRAIL_FLOOR)
            | Q(implied_odds_over__gt=PROBABILITY_GUARDRAIL_CEILING)
            | Q(implied_odds_under__lt=PROBABILITY_GUARDRAIL_FLOOR)
            | Q(implied_odds_under__gt=PROBABILITY_GUARDRAIL_CEILING)
        )

        invalid_qs = Market.objects.select_related("stock").filter(invalid_filter)
        if normalized_symbols:
            invalid_qs = invalid_qs.filter(stock__symbol__in=normalized_symbols)

        affected_symbols = sorted(set(invalid_qs.values_list("stock__symbol", flat=True)))
        active_invalid_qs = invalid_qs.filter(is_active=True)
        inactive_orphan_invalid_qs = invalid_qs.filter(is_active=False).annotate(
            bet_count=Count("bets")
        ).filter(bet_count=0)

        total_invalid = invalid_qs.count()
        active_invalid = active_invalid_qs.count()
        inactive_orphan_invalid = inactive_orphan_invalid_qs.count()

        self.stdout.write(
            "Found "
            f"{total_invalid} invalid market(s) outside the "
            f"{int(PROBABILITY_GUARDRAIL_FLOOR * 100)}%-{int(PROBABILITY_GUARDRAIL_CEILING * 100)}% guardrail. "
            f"Active invalid: {active_invalid}. "
            f"Inactive orphan invalid: {inactive_orphan_invalid}."
        )
        if normalized_symbols:
            self.stdout.write(f"Scoped symbols: {', '.join(normalized_symbols)}")

        if not total_invalid:
            self.stdout.write("No out-of-range markets found.")
            return

        if dry_run:
            self.stdout.write("Dry run only. No database changes were made.")
            return

        deactivated = active_invalid_qs.update(is_active=False)
        deleted = 0
        if hard_delete_orphans:
            deleted, _ = inactive_orphan_invalid_qs.delete()

        for symbol in affected_symbols:
            cache.delete(f"market_grouped_{symbol}")
        cache.delete("stock_admin_list")

        self.stdout.write(
            f"Completed cleanup. Deactivated {deactivated} active invalid market(s). "
            f"Deleted {deleted} inactive orphan invalid market(s)."
        )
