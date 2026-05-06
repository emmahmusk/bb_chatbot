from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction

from mkt.models import OptionData


class Command(BaseCommand):
    help = (
        "Purge OptionData rows for an old feed provider. "
        "Defaults to SteadyAPI-style contract IDs containing '|'."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--pattern",
            default="|",
            help="Substring pattern used to identify provider-specific contract IDs. Default: '|'.",
        )
        parser.add_argument(
            "--symbols",
            nargs="+",
            help="Optional list of symbols to limit the purge to (e.g. AAPL MSFT TSLA).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without deleting anything.",
        )

    def handle(self, *args, **options):
        pattern = options["pattern"]
        symbols = options.get("symbols") or []
        dry_run = options["dry_run"]

        queryset = OptionData.objects.filter(contract_id__contains=pattern)
        normalized_symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
        if normalized_symbols:
            queryset = queryset.filter(symbol__in=normalized_symbols)

        total_rows = queryset.count()
        if total_rows == 0:
            self.stdout.write(
                self.style.WARNING("No matching OptionData rows found for the requested purge.")
            )
            return

        rows_by_symbol = list(
            queryset.order_by("symbol")
            .values_list("symbol")
        )
        counts_by_symbol = {}
        for (symbol,) in rows_by_symbol:
            counts_by_symbol[symbol] = counts_by_symbol.get(symbol, 0) + 1

        affected_symbols = sorted(counts_by_symbol.keys())
        sample_contracts = list(
            queryset.order_by("symbol", "contract_id")
            .values_list("contract_id", flat=True)[:10]
        )

        self.stdout.write(
            f"Matched {total_rows} OptionData rows across {len(affected_symbols)} symbols."
        )
        self.stdout.write(f"Pattern: {pattern!r}")
        self.stdout.write(f"Symbols: {', '.join(affected_symbols)}")
        self.stdout.write("Counts by symbol:")
        for symbol in affected_symbols:
            self.stdout.write(f"  - {symbol}: {counts_by_symbol[symbol]}")

        if sample_contracts:
            self.stdout.write("Sample contract IDs:")
            for contract_id in sample_contracts:
                self.stdout.write(f"  - {contract_id}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run only. No rows were deleted.")
            )
            self.stdout.write(
                "Next step: rerun without `--dry-run`, then trigger Alpha Vantage reingestion."
            )
            return

        with transaction.atomic():
            deleted_count, _ = queryset.delete()

        for symbol in affected_symbols:
            cache.delete(f"market_grouped_{symbol}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} OptionData rows and cleared grouped market cache for {len(affected_symbols)} symbols."
            )
        )
        self.stdout.write(
            "Next step: trigger Alpha Vantage reingestion for the affected symbols so fresh OptionData and Market rows are rebuilt."
        )
