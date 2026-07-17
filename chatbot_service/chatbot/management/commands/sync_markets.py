from django.core.management.base import BaseCommand
from chatbot.services.indexer import sync_market_index


class Command(BaseCommand):
    help = "Fetch public BullBear markets and refresh their OpenAI embeddings."

    def add_arguments(self, parser):
        parser.add_argument("--symbol", action="append", dest="symbols")
        parser.add_argument("--prune", action="store_true")

    def handle(self, *args, **options):
        result = sync_market_index(symbols=options["symbols"], prune=options["prune"])
        self.stdout.write(self.style.SUCCESS(str(result)))
