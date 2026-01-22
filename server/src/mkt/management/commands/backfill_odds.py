from django.core.management.base import BaseCommand
from betengine.models import Market
from betengine.utils import implied_probability_to_american  # Adjust import if needed

class Command(BaseCommand):
    help = "Backfills missing display_odds_over and display_odds_under using implied odds."

    def handle(self, *args, **kwargs):
        updated_count = 0

        for market in Market.objects.all():
            updated = False
            if not market.display_odds_over and market.implied_odds_over > 0:
                market.display_odds_over = implied_probability_to_american(market.implied_odds_over)
                updated = True

            if not market.display_odds_under and market.implied_odds_under > 0:
                market.display_odds_under = implied_probability_to_american(market.implied_odds_under)
                updated = True

            if updated:
                market.save()
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Backfill complete: {updated_count} markets updated."))
