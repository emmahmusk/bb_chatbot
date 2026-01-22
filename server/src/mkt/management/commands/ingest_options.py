from django.core.management.base import BaseCommand
from django_q.tasks import async_task

class Command(BaseCommand):
    help = "Enqueue Alpha Vantage options ingestion via Django Q"

    def add_arguments(self, parser):
        parser.add_argument("--symbols", nargs="+", required=True, help="List of symbols (e.g. AAPL MSFT)")
        parser.add_argument("--api_key", required=True, help="Alpha Vantage API key")
        parser.add_argument("--date", help="Date in YYYY-MM-DD format (optional)")

    def handle(self, *args, **options):
        symbols = options["symbols"]
        api_key = options["api_key"]
        date = options.get("date")

        async_task("mkt.tasks.ingest_historical_options", symbols, api_key, date)
        self.stdout.write(
            self.style.SUCCESS(f"Task enqueued for symbols: {symbols} on date: {date or 'latest'}")
        )
