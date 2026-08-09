# Create your tests here.
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Bet, Competition, Market, Stock


class MarketListPlatformVolumeOrderingTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="volume-test-user",
            password="test-password",
        )
        self.expiry = timezone.now().date() + timedelta(days=30)

        self.markets = {}
        for symbol in ("AAPL", "MSFT", "TSLA"):
            stock = Stock.objects.create(symbol=symbol, company_name=symbol)
            self.markets[symbol] = Market.objects.create(
                stock=stock,
                target_price=Decimal("100.00"),
                expiry_date=self.expiry,
                implied_odds_over=Decimal("0.5000"),
                implied_odds_under=Decimal("0.5000"),
                display_odds_over="-110",
                display_odds_under="-110",
                total_volume=999999,
            )

    def _bet(self, symbol, amount, **overrides):
        values = {
            "user": self.user,
            "market": self.markets[symbol],
            "amount_wagered": Decimal(amount),
            "odds_at_placement": "-110",
            "chosen_outcome": "over",
            "status": "pending",
            "is_placed": True,
        }
        values.update(overrides)
        return Bet.objects.create(**values)

    def _symbols(self, query=""):
        response = self.client.get(f"{reverse('market-list')}{query}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [item["stock"]["symbol"] for item in response.data["results"]]

    def test_default_list_ranks_tickers_by_valid_platform_wager_volume(self):
        self._bet("AAPL", "25.00")
        self._bet("MSFT", "100.00")

        self.assertEqual(self._symbols(), ["MSFT", "AAPL", "TSLA"])

    def test_trending_list_uses_the_same_platform_volume_ranking(self):
        self._bet("AAPL", "75.00")
        self._bet("MSFT", "10.00")

        self.assertEqual(
            self._symbols("?trending=true"),
            ["AAPL", "MSFT", "TSLA"],
        )

    def test_invalid_wagers_do_not_affect_ranking(self):
        self._bet("AAPL", "20.00")
        self._bet("MSFT", "500.00", status="void")
        self._bet("TSLA", "700.00", is_placed=False)

        self.assertEqual(self._symbols(), ["AAPL", "MSFT", "TSLA"])

    def test_competition_wagers_do_not_inflate_platform_volume(self):
        now = timezone.now()
        competition = Competition.objects.create(
            name="Volume test competition",
            creator=self.user,
            start_date=now,
            end_date=now + timedelta(days=7),
        )
        self._bet("AAPL", "20.00")
        self._bet("MSFT", "500.00", competition=competition)

        self.assertEqual(self._symbols(), ["AAPL", "MSFT", "TSLA"])

    def test_external_market_volume_does_not_affect_ticker_ranking(self):
        self.markets["TSLA"].total_volume = 999999999
        self.markets["TSLA"].save(update_fields=["total_volume"])
        self._bet("AAPL", "1.00")

        self.assertEqual(self._symbols(), ["AAPL", "MSFT", "TSLA"])
