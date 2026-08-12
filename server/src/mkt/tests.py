from decimal import Decimal

from django.test import SimpleTestCase

from .alpha_vantage_data_fetcher import calculate_true_probabilities
from .odds_transformer import OddsCalculator


class NoVigProbabilityTests(SimpleTestCase):
    def test_alpha_vantage_probability_pair_is_true_and_complementary(self):
        prob_over, prob_under = calculate_true_probabilities(
            Decimal("40"),
            Decimal("40"),
        )

        self.assertEqual(prob_over, Decimal("0.4000"))
        self.assertEqual(prob_under, Decimal("0.6000"))
        self.assertEqual(prob_over + prob_under, Decimal("1.0000"))

    def test_odds_calculator_does_not_adjust_probability_for_vig(self):
        calculator = OddsCalculator(vig=Decimal("0.09"))
        probability = Decimal("0.4000")

        self.assertEqual(calculator.vig, Decimal("0.00"))
        self.assertEqual(
            calculator.adjust_odds_with_vig(probability, "over"),
            probability,
        )
