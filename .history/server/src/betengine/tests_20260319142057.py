from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from betengine.models import Bet, Market, ParlayBet, Stock
from user.models import Transaction, Wallet


User = get_user_model()


class BBCPayoutCreditRegressionTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.user = User.objects.create_user(
			username="bbc_test_user",
			email="bbc_test_user@example.com",
			password="secure-test-pass-123",
		)
		self.client.force_authenticate(user=self.user)
		self.wallet, _ = Wallet.objects.get_or_create(
			user=self.user,
			defaults={"balance": Decimal("0.00"), "coin_balance": Decimal("0.00")},
		)
		self.wallet.coin_balance = Decimal("0.00")
		self.wallet.balance = Decimal("0.00")
		self.wallet.save(update_fields=["coin_balance", "balance", "updated_at"])

	def _create_market(self, symbol: str, target_price: str):
		stock = Stock.objects.create(symbol=symbol, company_name=f"{symbol} Inc")
		return Market.objects.create(
			stock=stock,
			target_price=Decimal(target_price),
			expiry_date=date.today(),
			implied_odds_over=Decimal("0.5000"),
			implied_odds_under=Decimal("0.5000"),
			display_odds_over="-110",
			display_odds_under="-110",
			is_active=True,
		)

	def test_bulk_credit_single_bet_credits_exact_bbc_payout(self):
		market = self._create_market(symbol="SGLBBC", target_price="100.00")
		payout_amount = Decimal("12.34")

		bet = Bet.objects.create(
			user=self.user,
			market=market,
			amount_wagered=Decimal("5.00"),
			odds_at_placement="+150",
			chosen_outcome="over",
			status="won",
			payout_amount=payout_amount,
			is_parlay_leg=False,
			is_paid=False,
		)

		response = self.client.post(reverse("credit-wallets"), {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)

		self.wallet.refresh_from_db()
		bet.refresh_from_db()

		self.assertEqual(self.wallet.coin_balance, payout_amount)
		self.assertTrue(bet.is_paid)

		tx = Transaction.objects.filter(wallet=self.wallet, reference__contains=f"TRX-BET-CR-{bet.id}").latest("id")
		self.assertEqual(tx.transaction_type, Transaction.CREDIT)
		self.assertEqual(tx.amount, payout_amount)
		self.assertIn("BBC", tx.description)

	def test_bulk_credit_parlay_credits_exact_bbc_payout(self):
		market_one = self._create_market(symbol="PRLBBC1", target_price="150.00")
		market_two = self._create_market(symbol="PRLBBC2", target_price="250.00")
		payout_amount = Decimal("33.21")

		parlay = ParlayBet.objects.create(
			user=self.user,
			amount_wagered=Decimal("10.00"),
			combined_odds="+232",
			status="won",
			payout_amount=payout_amount,
		)

		leg_one = Bet.objects.create(
			user=self.user,
			market=market_one,
			amount_wagered=Decimal("10.00"),
			odds_at_placement="+110",
			chosen_outcome="over",
			status="won",
			payout_amount=Decimal("21.00"),
			is_parlay_leg=True,
			parlay_bet=parlay,
			is_paid=False,
		)
		leg_two = Bet.objects.create(
			user=self.user,
			market=market_two,
			amount_wagered=Decimal("10.00"),
			odds_at_placement="+110",
			chosen_outcome="under",
			status="won",
			payout_amount=Decimal("21.00"),
			is_parlay_leg=True,
			parlay_bet=parlay,
			is_paid=False,
		)

		response = self.client.post(reverse("credit-wallets"), {}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)

		self.wallet.refresh_from_db()
		leg_one.refresh_from_db()
		leg_two.refresh_from_db()

		self.assertEqual(self.wallet.coin_balance, payout_amount)
		self.assertTrue(leg_one.is_paid)
		self.assertTrue(leg_two.is_paid)

		tx = Transaction.objects.filter(wallet=self.wallet, reference__contains=f"TRX-PARLAY-CR-{parlay.id}").latest("id")
		self.assertEqual(tx.transaction_type, Transaction.CREDIT)
		self.assertEqual(tx.amount, payout_amount)
		self.assertIn("BBC", tx.description)
