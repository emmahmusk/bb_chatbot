from decimal import Decimal, ROUND_HALF_UP

COIN_QUANTIZER = Decimal("0.01")
CASH_QUANTIZER = Decimal("0.01")

RANDOM_CONVERSION_TABLE = [
    {
        "tier": "starter",
        "min_cash": Decimal("0.00"),
        "max_cash": Decimal("49.99"),
        "coins_per_dollar": Decimal("8.00"),
    },
    {
        "tier": "standard",
        "min_cash": Decimal("50.00"),
        "max_cash": Decimal("199.99"),
        "coins_per_dollar": Decimal("10.00"),
    },
    {
        "tier": "pro",
        "min_cash": Decimal("200.00"),
        "max_cash": Decimal("9999999.99"),
        "coins_per_dollar": Decimal("12.00"),
    },
]


def get_conversion_table_payload():
    payload = []
    for row in RANDOM_CONVERSION_TABLE:
        payload.append(
            {
                "tier": row["tier"],
                "min_cash": str(row["min_cash"].quantize(CASH_QUANTIZER)),
                "max_cash": str(row["max_cash"].quantize(CASH_QUANTIZER)),
                "coins_per_dollar": str(row["coins_per_dollar"].quantize(COIN_QUANTIZER)),
            }
        )
    return payload


def get_rate_for_cash_amount(cash_amount: Decimal) -> Decimal:
    for row in RANDOM_CONVERSION_TABLE:
        if row["min_cash"] <= cash_amount <= row["max_cash"]:
            return row["coins_per_dollar"]
    return RANDOM_CONVERSION_TABLE[0]["coins_per_dollar"]


def get_default_redemption_rate() -> Decimal:
    return Decimal("10.00")


def cash_to_coins(cash_amount: Decimal) -> Decimal:
    rate = get_rate_for_cash_amount(cash_amount)
    return (cash_amount * rate).quantize(COIN_QUANTIZER, rounding=ROUND_HALF_UP)


def coins_to_cash(coin_amount: Decimal) -> Decimal:
    rate = get_default_redemption_rate()
    return (coin_amount / rate).quantize(CASH_QUANTIZER, rounding=ROUND_HALF_UP)
