# Create your tests here.
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from user.models import CompetitionMember

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


class CompetitionLeaderboardTests(APITestCase):
    def setUp(self):
        now = timezone.now()
        self.competition = Competition.objects.create(
            name="Leaderboard test",
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=7),
            status="active",
            scoring_method="net_profit",
        )
        stock = Stock.objects.create(symbol="COMP", company_name="Competition Test")
        self.market = Market.objects.create(
            stock=stock,
            target_price=Decimal("100.00"),
            expiry_date=now.date() + timedelta(days=3),
            implied_odds_over=Decimal("0.5000"),
            implied_odds_under=Decimal("0.5000"),
            display_odds_over="-110",
            display_odds_under="-110",
        )

        self.members = {}
        for username in ("alpha", "beta", "gamma", "zero", "delta"):
            user = get_user_model().objects.create_user(
                username=username,
                password="test-password",
            )
            self.members[username] = CompetitionMember.objects.create(
                competition=self.competition,
                user=user,
            )

        self._bet("alpha", "100.00", "won", "300.00")
        self._bet("gamma", "100.00", "won", "150.00")
        self._bet("delta", "75.00", "lost", "0.00")

        # This large wager is outside the competition and must not affect beta's score.
        Bet.objects.create(
            user=self.members["beta"].user,
            market=self.market,
            amount_wagered=Decimal("1000.00"),
            payout_amount=Decimal("5000.00"),
            odds_at_placement="+400",
            chosen_outcome="over",
            status="won",
        )

    def _bet(self, username, amount, bet_status, payout):
        return Bet.objects.create(
            user=self.members[username].user,
            competition=self.competition,
            market=self.market,
            amount_wagered=Decimal(amount),
            payout_amount=Decimal(payout),
            odds_at_placement="-110",
            chosen_outcome="over",
            status=bet_status,
        )

    def test_leaderboard_orders_live_scores_and_gives_equal_scores_equal_rank(self):
        response = self.client.get(
            reverse("competition-leaderboard", args=[self.competition.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["results"]
        self.assertEqual(
            [row["username"] for row in rows],
            ["alpha", "gamma", "beta", "zero", "delta"],
        )
        self.assertEqual(
            [row["score"] for row in rows],
            ["200.00", "50.00", "0.00", "0.00", "-75.00"],
        )
        self.assertEqual([row["rank"] for row in rows], [1, 2, 3, 3, 5])


class CompetitionMembershipFilterTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="member-filter-user",
            password="test-password",
        )
        self.client.force_authenticate(self.user)
        now = timezone.now()

        self.competitions = {
            "registration": Competition.objects.create(
                name="Upcoming",
                start_date=now + timedelta(days=1),
                end_date=now + timedelta(days=8),
                status="registration",
            ),
            "active": Competition.objects.create(
                name="Active",
                start_date=now - timedelta(days=1),
                end_date=now + timedelta(days=6),
                status="active",
            ),
            "completed": Competition.objects.create(
                name="Completed",
                start_date=now - timedelta(days=10),
                end_date=now - timedelta(days=2),
                status="completed",
            ),
        }
        for competition in self.competitions.values():
            CompetitionMember.objects.create(
                competition=competition,
                user=self.user,
            )

    def _names(self, status_filter):
        response = self.client.get(
            reverse("competition-membership-list"),
            {"status": status_filter},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [row["competition_name"] for row in response.data["results"]]

    def test_live_filter_contains_registration_and_active_memberships(self):
        self.assertEqual(self._names("live"), ["Active", "Upcoming"])

    def test_completed_filter_only_contains_finished_memberships(self):
        self.assertEqual(self._names("completed"), ["Completed"])
