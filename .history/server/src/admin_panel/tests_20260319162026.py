from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from betengine.models import Bet, Market, Stock


User = get_user_model()


class StockSettlementDetailViewTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.admin_user = User.objects.create_user(
			username="admin_settlement",
			email="admin_settlement@example.com",
			password="test-pass-123",
			is_staff=True,
		)
		self.client.force_authenticate(user=self.admin_user)

		self.stock = Stock.objects.create(
			symbol="STLMT",
			company_name="Settlement Inc",
		)

		self.expiry_settled = date.today() + timedelta(days=1)
		self.expiry_unsettled = date.today() + timedelta(days=2)

		self.market_settled = Market.objects.create(
			stock=self.stock,
			target_price=Decimal("100.00"),
			expiry_date=self.expiry_settled,
			outcome_type="over",
			implied_odds_over=Decimal("0.5000"),
			implied_odds_under=Decimal("0.5000"),
			display_odds_over="-110",
			display_odds_under="-110",
			is_active=True,
		)
		self.market_unsettled = Market.objects.create(
			stock=self.stock,
			target_price=Decimal("120.00"),
			expiry_date=self.expiry_unsettled,
			outcome_type="over",
			implied_odds_over=Decimal("0.5000"),
			implied_odds_under=Decimal("0.5000"),
			display_odds_over="-110",
			display_odds_under="-110",
			is_active=True,
		)

		bettor = User.objects.create_user(
			username="bettor_settlement",
			email="bettor_settlement@example.com",
			password="test-pass-123",
		)

		Bet.objects.create(
			user=bettor,
			market=self.market_settled,
			amount_wagered=Decimal("10.00"),
			odds_at_placement="+120",
			chosen_outcome="over",
			status="won",
			payout_amount=Decimal("22.00"),
		)
		Bet.objects.create(
			user=bettor,
			market=self.market_settled,
			amount_wagered=Decimal("8.00"),
			odds_at_placement="+120",
			chosen_outcome="under",
			status="lost",
			payout_amount=Decimal("0.00"),
		)
		Bet.objects.create(
			user=bettor,
			market=self.market_unsettled,
			amount_wagered=Decimal("12.00"),
			odds_at_placement="+120",
			chosen_outcome="over",
			status="pending",
			payout_amount=Decimal("0.00"),
		)

	def test_grouped_settlement_buckets_and_flags(self):
		response = self.client.get(
			reverse("stock-settlement-detail"),
			{"symbol": self.stock.symbol},
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		payload = response.json()

		self.assertTrue(payload["has_grouped_settlements"])
		self.assertTrue(payload["has_grouped_settlements_settled"])
		self.assertTrue(payload["has_grouped_settlements_unsettled"])

		settled_groups = payload["grouped_settlements_by_bucket"]["settled"]
		unsettled_groups = payload["grouped_settlements_by_bucket"]["unsettled"]

		self.assertEqual(len(settled_groups), 1)
		self.assertEqual(len(unsettled_groups), 1)

		settled_expiry = settled_groups[0]["expiry_date"]
		unsettled_expiry = unsettled_groups[0]["expiry_date"]
		self.assertNotEqual(settled_expiry, unsettled_expiry)

	def test_status_filter_unsettled_hides_empty_settled_expiries(self):
		response = self.client.get(
			reverse("stock-settlement-detail"),
			{"symbol": self.stock.symbol, "status": "unsettled"},
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		payload = response.json()

		self.assertTrue(payload["has_grouped_settlements"])
		self.assertEqual(len(payload["grouped_settlements"]), 1)

		only_group = payload["grouped_settlements"][0]
		for market_row in only_group["markets"]:
			self.assertGreater(market_row["status_counts"]["pending"], 0)
			self.assertEqual(market_row["status_counts"]["won"], 0)
			self.assertEqual(market_row["status_counts"]["lost"], 0)
			self.assertEqual(market_row["status_counts"]["void"], 0)
