from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from decimal import Decimal, ROUND_HALF_UP


def round_two_places(val):
    return float(Decimal(val).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def apply_vig(p_over, p_under):
    """
    Normalize the probabilities so they sum to 1 after applying a vig (market margin).
    """
    total = p_over + p_under
    if total == 0:
        return 0.0, 0.0
    return round(p_over / total, 4), round(p_under / total, 4)


def implied_to_american(prob):
    if prob <= 0 or prob >= 1:
        return None
    return str(round(-100 * prob / (1 - prob))) if prob > 0.5 else f"+{round(100 * (1 - prob) / prob)}"


def implied_to_decimal(prob):
    if prob <= 0 or prob >= 1:
        return None
    return round_two_places(1 / prob)


def american_to_fractional(american):
    if not american:
        return None
    american = int(american)
    if american > 0:
        return f"{american}/100"
    else:
        return f"100/{abs(american)}"


def build_odds(probability):
    if probability <= 0 or probability >= 1:
        return {
            "american": None,
            "decimal": None,
            "fractional": None,
            "preferred": {"format": "decimal", "value": None}
        }

    decimal_odds = implied_to_decimal(probability)
    american_odds = implied_to_american(probability)
    fractional_odds = american_to_fractional(american_odds)

    return {
        "american": american_odds,
        "decimal": str(decimal_odds),
        "fractional": fractional_odds,
        "preferred": {
            "format": "decimal",
            "value": str(decimal_odds)
        }
    }


class OptionOddsView(APIView):
    """
    Given raw implied probabilities for over and under, apply vig and return full odds.
    """

    def post(self, request):
        try:
            implied_over = float(request.data.get("implied_odds_over"))
            implied_under = float(request.data.get("implied_odds_under"))

            # Step 1: Apply vig normalization
            adjusted_over, adjusted_under = apply_vig(implied_over, implied_under)

            # Step 2: Format odds
            odds_over = build_odds(adjusted_over)
            odds_under = build_odds(adjusted_under)

            return Response({
                "implied_probability_over": implied_over,
                "implied_probability_under": implied_under,
                "adjusted_probability_over": adjusted_over,
                "adjusted_probability_under": adjusted_under,
                "odds_over": odds_over,
                "odds_under": odds_under,
            })

        except Exception as e:
            return Response(
                {"error": f"Invalid input or server error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )