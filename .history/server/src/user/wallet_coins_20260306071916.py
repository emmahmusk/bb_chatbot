from decimal import Decimal, ROUND_HALF_UP
from math import sqrt

COIN_QUANTIZER = Decimal("0.01")
CASH_QUANTIZER = Decimal("0.01")

BASE_RATE = Decimal("8.00")
RATE_SLOPE = Decimal("0.01")


def get_formula_payload():
    return {
        "model": "quadratic-rate",
        "base_rate": str(BASE_RATE.quantize(Decimal("0.00"))),
        "rate_slope": str(RATE_SLOPE.quantize(Decimal("0.0000"))),
        "cash_to_coins": "coins = cash * (base_rate + rate_slope * cash)",
        "coins_to_cash": "cash = (-base_rate + sqrt(base_rate^2 + 4*rate_slope*coins)) / (2*rate_slope)",
    }


def get_rate_for_cash_amount(cash_amount: Decimal) -> Decimal:
    return (BASE_RATE + (RATE_SLOPE * cash_amount)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def cash_to_coins(cash_amount: Decimal) -> Decimal:
    cash_amount = Decimal(cash_amount)
    if cash_amount <= 0:
        return Decimal("0.00")
    dynamic_rate = BASE_RATE + (RATE_SLOPE * cash_amount)
    return (cash_amount * dynamic_rate).quantize(COIN_QUANTIZER, rounding=ROUND_HALF_UP)


def coins_to_cash(coin_amount: Decimal) -> Decimal:
    coin_amount = Decimal(coin_amount)
    if coin_amount <= 0:
        return Decimal("0.00")

    if RATE_SLOPE == 0:
        return (coin_amount / BASE_RATE).quantize(CASH_QUANTIZER, rounding=ROUND_HALF_UP)

    discriminant = (BASE_RATE ** 2) + (Decimal("4") * RATE_SLOPE * coin_amount)
    cash_value = (-BASE_RATE + Decimal(str(sqrt(float(discriminant))))) / (Decimal("2") * RATE_SLOPE)
    return cash_value.quantize(CASH_QUANTIZER, rounding=ROUND_HALF_UP)


def explain_cash_to_coins(cash_amount: Decimal):
    cash_amount = Decimal(cash_amount)
    rate = get_rate_for_cash_amount(cash_amount)
    coins = cash_to_coins(cash_amount)
    return {
        "cash_amount": str(cash_amount.quantize(CASH_QUANTIZER, rounding=ROUND_HALF_UP)),
        "applied_rate": str(rate),
        "coins": str(coins),
        "explanation": f"coins = {cash_amount.quantize(CASH_QUANTIZER)} * ({BASE_RATE} + {RATE_SLOPE}*{cash_amount.quantize(CASH_QUANTIZER)}) = {coins}",
    }


def explain_coins_to_cash(coin_amount: Decimal):
    coin_amount = Decimal(coin_amount)
    cash_value = coins_to_cash(coin_amount)
    return {
        "coin_amount": str(coin_amount.quantize(COIN_QUANTIZER, rounding=ROUND_HALF_UP)),
        "cash": str(cash_value),
        "explanation": f"cash = (-{BASE_RATE} + sqrt({BASE_RATE}^2 + 4*{RATE_SLOPE}*{coin_amount.quantize(COIN_QUANTIZER)})) / (2*{RATE_SLOPE}) = {cash_value}",
    }
