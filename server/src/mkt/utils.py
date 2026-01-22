import logging
import math
from decimal import Decimal, getcontext
from typing import Any, Dict, Optional, Union
import requests
from datetime import datetime
from typing import List
from decimal import Decimal, ROUND_HALF_UP

from scipy.optimize import newton  # For implied volatility solver
from scipy.stats import norm       # For Black-Scholes

logger = logging.getLogger(__name__)
getcontext().prec = 10  # Set Decimal precision for calculations

# --- Black-Scholes Option Pricing ---
def black_scholes_price(
    option_type: str,  # 'c' for call, 'p' for put
    S: Decimal,  # Current stock price
    K: Decimal,  # Strike price
    t: Decimal,  # Time to expiry in years
    r: Decimal,  # Risk-free rate
    sigma: Decimal,  # Volatility (implied volatility)
    q: Decimal = Decimal("0.00"),  # Dividend yield (default 0)
) -> Decimal:
    if t <= 0:
        return Decimal("0")
    S_f, K_f, t_f, r_f, sigma_f, q_f = (
        float(S), float(K), float(t), float(r), float(sigma), float(q)
    )
    if sigma_f <= 1e-9 or t_f <= 1e-9:
        return Decimal("0")
    sqrt_t = math.sqrt(t_f)
    sigma_sqrt_t = sigma_f * sqrt_t
    d1 = (math.log(S_f / K_f) + (r_f - q_f + 0.5 * sigma_f ** 2) * t_f) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t
    try:
        if option_type == "c":
            price = S_f * math.exp(-q_f * t_f) * norm.cdf(d1) - K_f * math.exp(-r_f * t_f) * norm.cdf(d2)
        elif option_type == "p":
            price = K_f * math.exp(-r_f * t_f) * norm.cdf(-d2) - S_f * math.exp(-q_f * t_f) * norm.cdf(-d1)
        else:
            raise ValueError("Option type must be 'c' (call) or 'p' (put).")
        return Decimal(str(max(0.0, price)))
    except Exception as e:
        logger.error(f"Error in Black-Scholes price calculation: {e}", exc_info=True)
        return Decimal("0")

# --- Implied Volatility Solver ---
def implied_volatility_solver(
    market_price: Decimal,
    option_type: str,
    S: Decimal,
    K: Decimal,
    t: Decimal,
    r: Decimal,
    q: Decimal = Decimal("0.00"),
    initial_guess: Decimal = Decimal("0.50"),
) -> Optional[Decimal]:
    if market_price <= 0 or t <= 0:
        return Decimal("0")
    def f(sigma_float):
        sigma_val = Decimal(str(max(1e-9, sigma_float)))
        calculated_price = black_scholes_price(option_type, S, K, t, r, sigma_val, q)
        return float(calculated_price - market_price)
    def vega(sigma_float):
        sigma_val = Decimal(str(max(1e-9, sigma_float)))
        t_f = float(t)
        if t_f <= 1e-9 or sigma_val <= 1e-9:
            return 1e-9
        d1 = (math.log(float(S / K)) + (float(r) - float(q) + 0.5 * float(sigma_val) ** 2) * t_f) / (float(sigma_val) * math.sqrt(t_f))
        vega_val = float(S) * math.exp(-float(q) * t_f) * norm.pdf(d1) * math.sqrt(t_f)
        return max(1e-9, vega_val)
    try:
        iv_float = newton(f, float(initial_guess), fprime=vega, tol=1e-6, maxiter=100)
        if 0.01 <= iv_float <= 5.0:
            return Decimal(str(iv_float))
        else:
            logger.warning(f"Implied volatility {iv_float:.4f} out of reasonable range [0.01, 5.0].")
            return None
    except Exception as e:
        logger.error(f"Implied volatility solver failed: {e}", exc_info=True)
        return None

# --- Implied Probability Calculation ---
def calculate_implied_probability_for_market_outcome(
    market_data: Dict[str, Any],
    target_price: Decimal,
    outcome_type: str,  # 'over' or 'under'
) -> Optional[Decimal]:
    S = market_data.get("current_stock_price")
    t = market_data.get("time_to_expiry_years")
    calls_data = market_data.get("calls_data", [])
    puts_data = market_data.get("puts_data", [])
    r = market_data.get("risk_free_rate")
    q = market_data.get("dividend_yield", Decimal("0.00"))
    
    print(f"Calculating implied probability for target price {target_price} with outcome type '{outcome_type}'")
    print(f"Calculating implied probability for calls_data {calls_data} with puts_data '{puts_data}'")
    if not all([S, t, r is not None]):
        logger.error("Missing data for implied probability calculation.")
        return None
    if not (calls_data or puts_data) or t <= 0:
        logger.warning("No valid options data or time to expiry <= 0.")
        return None
    all_options = []
    if calls_data:
        all_options.extend([{"type": "c", **opt} for opt in calls_data if opt.get("mid_price") is not None])
    if puts_data:
        all_options.extend([{"type": "p", **opt} for opt in puts_data if opt.get("mid_price") is not None])
    if not all_options:
        logger.warning("No valid ATM options for IV derivation.")
        return None
    all_options.sort(key=lambda x: abs(x["strike"] - S))
    atm_option = all_options[0]
    K_iv = atm_option["strike"]
    market_price = atm_option["mid_price"]
    opt_type = atm_option["type"]
    iv = implied_volatility_solver(market_price, opt_type, S, K_iv, t, r, q)
    if iv is None:
        logger.warning("Could not calculate reliable IV. Skipping implied odds.")
        return None
    sigma = iv
    S_f = float(S)
    target_price_f = float(target_price)
    t_f = float(t)
    r_f = float(r)
    q_f = float(q)
    sigma_f = float(sigma)
    if target_price_f <= 0:
        logger.error("Target price is zero or negative.")
        return None
    try:
        if sigma_f * math.sqrt(t_f) == 0:
            logger.warning("Denominator zero in d1/d2 calculation.")
            return Decimal("0")
        d1 = (math.log(S_f / target_price_f) + (r_f - q_f + 0.5 * sigma_f**2) * t_f) / (sigma_f * math.sqrt(t_f))
        d2 = d1 - sigma_f * math.sqrt(t_f)
        if outcome_type == "over":
            implied_prob = Decimal(str(norm.cdf(d2)))
        elif outcome_type == "under":
            implied_prob = Decimal(str(norm.cdf(-d2)))
        else:
            logger.error(f"Unsupported outcome_type: {outcome_type}")
            return None
        implied_prob = max(Decimal("0.0001"), min(Decimal("0.9999"), implied_prob))
        return implied_prob.quantize(Decimal("0.0001"))
    except Exception as e:
        logger.error(f"Error in implied probability calculation: {e}", exc_info=True)
        return None
def calculate_implied_probability_from_options(call_price, put_price, strike_price):
    """
    Risk-neutral implied probability the stock will finish above strike.
    Simplified: p = call / (call + put)
    """
    call_price = Decimal(call_price)
    put_price = Decimal(put_price)
    if call_price + put_price == 0:
        return Decimal("0.5")
    return call_price / (call_price + put_price)
# --- Odds Transformation ---

def probability_to_american_odds(prob: float):
    """
    Convert probability (0–1) to American odds (e.g., -110 or +150)
    """
    if prob <= 0 or prob >= 1:
        return None

    decimal_odds = 1 / prob
    if decimal_odds >= 2:
        return f"+{int((decimal_odds - 1) * 100)}"
    else:
        return f"-{int(100 / (decimal_odds - 1))}"

def decimal_prob_to_american(prob: Decimal) -> Decimal:
    try:
        if prob <= 0:
            return Decimal("1000.00")  # cap extremely small values
        if prob >= 1:
            return Decimal("1.01")  # lowest valid odds

        return Decimal("1.00") / prob
    except Exception as e:
        print(f"[decimal_odds_from_prob ERROR] Prob: {prob}, Error: {e}")
        return Decimal("2.00")  # fallback even odd
# def decimal_prob_to_american(prob: Decimal) -> int:
#     """
#     Converts a decimal probability to American odds.
#     """
#     if prob <= 0 or prob >= 1:
#         raise ValueError(f"Invalid probability for American odds conversion: {prob:.4f}")

#     if prob > Decimal("0.5"):
#         return int(-(prob / (1 - prob)) * 100)
#     else:
#         return int(((1 - prob) / prob) * 100)

# def apply_vig_and_format_odds(
#     implied_prob_over: Decimal,
#     implied_prob_under: Decimal,
#     vig_percentage: Decimal = Decimal("0.09"),
# ):
#     total_prob_sum = implied_prob_over + implied_prob_under
#     if total_prob_sum <= 0:
#         return "N/A", "N/A"
#     target_sum = Decimal("1") + vig_percentage
#     scaling_factor = total_prob_sum / target_sum
#     adj_prob_over = (implied_prob_over / scaling_factor).quantize(Decimal("0.0001"))
#     adj_prob_under = (implied_prob_under / scaling_factor).quantize(Decimal("0.0001"))
#     odds_over = convert_decimal_to_american_odds(adj_prob_over) or "N/A"
#     odds_under = convert_decimal_to_american_odds(adj_prob_under) or "N/A"
#     return odds_over, odds_under
def apply_vig(prob_over: float, prob_under: float, vig: float = 0.09):
    """
    Adjust the raw probabilities by adding vig (margin).
    """
    total = prob_over + prob_under
    if total == 0:
        return 0.5, 0.5

    # Scale the probabilities proportionally to account for vig
    factor = (1 + vig) / total
    prob_over_vig = prob_over * factor
    prob_under_vig = prob_under * factor

    return prob_over_vig, prob_under_vig

def american_to_decimal_odds(american_odds: str) -> Optional[Decimal]:
    try:
        american = Decimal(american_odds)
    except (ValueError, TypeError):
        logger.error(f"Invalid American odds string: {american_odds}")
        return None
    if american > 0:
        return (american / Decimal("100")) + Decimal("1")
    elif american < 0:
        return (Decimal("100") / abs(american)) + Decimal("1")
    else:
        logger.warning(f"American odds of 0 encountered: {american_odds}")
        return None

def decimal_to_implied_probability(decimal_odds: Decimal) -> Optional[Decimal]:
    if decimal_odds <= 0:
        logger.warning(f"Decimal odds must be positive: {decimal_odds}")
        return None
    return (Decimal("1") / decimal_odds).quantize(Decimal("0.0001"))


# def calculate_implied_probability_risk_neutral(call_price, put_price, strike_price, stock_price):
#     """
#     Calculate implied probability using a risk-neutral model.
#     """
#     if stock_price == 0:
#         return 0.5  # fallback

#     probability = (call_price - put_price + strike_price - stock_price) / (2 * strike_price)
#     return max(0, min(float(probability), 1))  # Clamp between 0 and 1


def get_time_to_expiry(expiration_date, current_date=None):
    # expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d").date()
    current_date = current_date or datetime.now().date()
    delta_days = (expiration_date - current_date).days
    return Decimal(delta_days) / Decimal("365")

# def calculate_implied_probability_risk_neutral(call_bid, call_ask, put_bid, put_ask):
#     """
#     Calculates over and under implied probabilities using call/put midprice ratio:
#     Over prob = CM / (CM + PM)
#     Under prob = PM / (CM + PM)
#     """

#     getcontext().prec = 8  # Ensure high precision for financial calculations

#     # Convert all values to Decimal
#     call_bid = Decimal(str(call_bid))
#     call_ask = Decimal(str(call_ask))
#     put_bid = Decimal(str(put_bid))
#     put_ask = Decimal(str(put_ask))

#     # Calculate mid prices
#     CM = (call_bid + call_ask) / 2
#     PM = (put_bid + put_ask) / 2

#     if CM == 0 and PM == 0:
#         # Explicitly skip this pair due to invalid price data
#         raise ValueError("Call and Put midprices are zero — skipping invalid data")

#     total = CM + PM
#     if total == 0:
#         raise ValueError("Total of CM + PM is zero — skipping this option pair")

#     # if (CM + PM) == 0:
#     #     return Decimal("0.5"), Decimal("0.5")  # Avoid division by zero (fallback)

#     # Apply formula
#     over_prob = CM / total
#     under_prob = PM / total

#     # Clamp for safety
#     over_prob = max(Decimal("0.0"), min(over_prob, Decimal("1.0")))
#     under_prob = max(Decimal("0.0"), min(under_prob, Decimal("1.0")))

#     return over_prob, under_prob

def calculate_implied_probability_risk_neutral(call_mark, put_mark):
    """
    Calculate over/under implied probabilities using the mark price for calls & puts.

    Over prob = CM / (CM + PM)
    Under prob = PM / (CM + PM)

    Args:
        call_mark (Decimal or str): Mark price for the call option.
        put_mark (Decimal or str): Mark price for the put option.

    Returns:
        tuple: (over_probability, under_probability)
    """
    getcontext().prec = 8  # Ensure precision

    # Convert to Decimal
    call_mark = Decimal(str(call_mark or 0))
    put_mark = Decimal(str(put_mark or 0))

    if call_mark <= 0 and put_mark <= 0:
        raise ValueError("Both call and put marks are zero or missing.")

    total = call_mark + put_mark
    if total <= 0:
        raise ValueError("Total of call and put marks is zero — invalid data.")

    over_prob = call_mark / total
    under_prob = put_mark / total

    # Clamp between 0 and 1 for safety
    over_prob = max(Decimal("0.0"), min(over_prob, Decimal("1.0")))
    under_prob = max(Decimal("0.0"), min(under_prob, Decimal("1.0")))

    return over_prob, under_prob

def get_side_and_american_odds(implied_prob: Decimal, odds_ladder: list[dict], vig: Decimal = Decimal("9.0")) -> tuple[str, Union[int, float]]:
    """
    Wrapper for ladder lookup. Returns side and corresponding American odds.
    """
    side, american_odds = get_american_odds_from_ladder(implied_prob, odds_ladder, vig)
    print(f"{side.capitalize()} American Odds: {american_odds}")
    return side, american_odds


def get_decimal_odds_from_american(side: str, american_odds: Union[int, float]) -> tuple[str, float]:
    """
    Converts American odds to decimal odds and associates it with the side.
    """
    decimal_odds = american_to_decimal_odds(american_odds)
    print(f"{side.capitalize()} Decimal Odds: {decimal_odds}")
    return side, decimal_odds


def format_vig_key(vig_percent: Decimal) -> str:
    rounded = (vig_percent * 2).to_integral_value(rounding=ROUND_HALF_UP) / 2
    whole = int(rounded)
    half = int((rounded - whole) * 10)

    if half == 0:
        return f"vig_{whole}_0_percent"
    elif half == 5:
        return f"vig_{whole}_5_percent"
    else:
        raise KeyError(f"No matching odds ladder key for {rounded}%. Allowed increments: 0.5")


def get_american_odds_from_ladder(
    prob_vig: Union[float, Decimal],
    odds_ladder: list[dict],
    vig_percent: Decimal
) -> tuple[str, Union[int, float]]:
    """
    Looks up American odds from the ladder by comparing prob_vig to each row's br_true_percent and br_true_percent_opposite.
    Returns a tuple of (side, american_odds)
    """
    if not isinstance(odds_ladder, list):
        raise ValueError("Expected odds_ladder to be a list of dictionaries")

    # Convert probability to percent rounded to nearest integer
    percent = int(round(float(prob_vig) * 100))
    vig_key = format_vig_key(vig_percent)

    for row in odds_ladder:
        br = row.get("br_true_percent")
        br_opposite = row.get("br_true_percent_opposite")
        odds_data = row.get(vig_key)

        if odds_data is None:
            continue  # skip rows without the desired vig key

        if br == percent:
            return "over", odds_data.get("home")
        elif br_opposite == percent:
            return "under", odds_data.get("away")

    raise ValueError(
        f"No odds found in ladder for {percent}% using vig {vig_percent} ({vig_key})"
    )



def normalize_american_odds(value: Decimal) -> int:
    """
    Normalize American odds:
    Return value as an integer.
    Odds ≥ 100 remain positive.
    """
    return int(abs(value)) if value >= 100 else int(value)


# def calculate_implied_probability_risk_neutral(call_bid, call_ask, put_bid, put_ask, strike_price, stock_price, risk_free_rate=Decimal("0.05"), expiration_date=None):
#     """
#     Estimate the risk-neutral probability that the stock will finish above the strike,
#     using midprice for call and put options.
#     """

#     from math import exp

#     time_to_expiry = get_time_to_expiry(expiration_date)

#     getcontext().prec = 8  # Adjust precision if needed

#     # Convert to Decimal if not already
#     strike_price = Decimal(strike_price)
#     stock_price = Decimal(stock_price)
#     call_bid = Decimal(call_bid)
#     call_ask = Decimal(call_ask)
#     put_bid = Decimal(put_bid)
#     put_ask = Decimal(put_ask)

#     # Compute midprices
#     call_mid = (call_bid + call_ask) / 2
#     put_mid = (put_bid + put_ask) / 2

#     # Discounted strike
#     discounted_strike = strike_price * Decimal(exp(float(-risk_free_rate * time_to_expiry)))

#     # Risk-neutral probability using midprices
#     numerator = call_mid - put_mid + discounted_strike - stock_price
#     probability = numerator / discounted_strike

#     # Clamp to [0, 1]
#     return max(Decimal("0.0"), min(probability, Decimal("1.0")))


def fetch_alpha_vantage_options(
    symbol: str,
    api_key: str,
    expiration_date: Optional[str] = None  # Format: 'YYYY-MM-DD'
) -> list:
    """
    Fetches historical option chain from Alpha Vantage and optionally filters by expiration date.

    Args:
        symbol (str): Stock symbol, e.g. 'AAPL'
        api_key (str): Your Alpha Vantage API key
        expiration_date (str, optional): Date filter in format 'YYYY-MM-DD'

    Returns:
        List[dict]: Parsed contracts (filtered if expiration_date is given)
    """
    url = f'https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&apikey={api_key}'
    resp = requests.get(url)
    data = resp.json().get("data", [])

    parsed = []

    for contract in data:
        try:
            exp_date = datetime.strptime(contract["expiration"], "%Y-%m-%d").date()

            # Skip if expiration_date is specified and doesn't match
            if expiration_date and str(exp_date) != expiration_date:
                continue

            parsed.append({
                "ticker": contract["contractID"],
                "symbol": contract["symbol"],
                "expiration": exp_date,
                "strike_price": float(contract["strike"]),
                "option_type": contract["type"].lower(),  # 'call' or 'put'
                "bid": float(contract.get("bid", 0)),
                "ask": float(contract.get("ask", 0)),
                "mark": float(contract.get("mark", 0)),
                "last": float(contract.get("last", 0)),
                "volume": int(contract.get("volume", 0)),
                "open_interest": int(contract.get("open_interest", 0)),
                "implied_volatility": float(contract.get("implied_volatility", 0)),
                "delta": float(contract.get("delta", 0)),
                "gamma": float(contract.get("gamma", 0)),
                "theta": float(contract.get("theta", 0)),
                "vega": float(contract.get("vega", 0)),
                "rho": float(contract.get("rho", 0)),
                "as_of": datetime.strptime(contract.get("date"), "%Y-%m-%d"),
            })
        except Exception as e:
            print(f"⚠️ Error parsing contract: {e}")

    return parsed

def fetch_underlying_price(symbol: str, api_key: str) -> float:
    """
    Fetches the latest (delayed) underlying stock price using Alpha Vantage.
    """
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": api_key,
    }

    try:
        resp = requests.get(url, params=params)
        data = resp.json()

        # Example response: { "Global Quote": { "05. price": "213.55", ... } }
        price_str = data["Global Quote"]["05. price"]
        return float(price_str)

    except Exception as e:
        print(f"Error fetching underlying price for {symbol}: {e}")
        return None
    














# def calculate_implied_probability_risk_neutral(call_price, put_price, strike_price, stock_price, risk_free_rate=0.05, time_to_expiry=0.1):
#     """
#     Estimate the risk-neutral probability that the stock will finish above the strike.
#     """
#     from math import exp

#     # Calculate discounted strike
#     discounted_strike = strike_price * Decimal(exp(-risk_free_rate * time_to_expiry))

#     # Risk-neutral probability of finishing above the strike (using simplified approximation)
#     numerator = call_price - put_price + discounted_strike - stock_price
#     probability = numerator / (discounted_strike)

#     # Clamp to [0, 1]
#     return max(0.0, min(probability, 1.0))

# def create_markets_from_options_data(stock_symbol: str, options_data: list):
#     """
#     Creates Market entries from option chain data for a given stock,
#     computing implied probabilities and converting them to American odds.
#     """
#     try:
#         stock = Stock.objects.get(symbol=stock_symbol)
#     except Stock.DoesNotExist:
#         print(f"❌ Stock not found: {stock_symbol}")
#         return

#     created_count = 0
#     skipped_count = 0

#     for option in options_data:
#         try:
#             strike_price = Decimal(option["strike"])
#             market_type = option["type"]  # 'call' or 'put'
#             expiration_str = option["expiration"]
#             expiry_date = datetime.strptime(expiration_str, "%Y-%m-%d").date()

#             bid = Decimal(option.get("bid", "0"))
#             ask = Decimal(option.get("ask", "0"))

#             # Skip if any key data is missing or invalid
#             if strike_price <= 0 or bid == 0 or ask == 0:
#                 continue

#             # Check if both markets already exist before doing anything
#             over_exists = Market.objects.filter(
#                 stock=stock, target_price=strike_price, expiry_date=expiry_date, outcome_type="over"
#             ).exists()
#             under_exists = Market.objects.filter(
#                 stock=stock, target_price=strike_price, expiry_date=expiry_date, outcome_type="under"
#             ).exists()

#             if over_exists and under_exists:
#                 skipped_count += 2
#                 continue

#             # Estimate implied probabilities
#             implied_prob_over = sanitize_probability(estimate_implied_probability(bid, ask))
#             implied_prob_under = sanitize_probability(round(Decimal("1.0") - implied_prob_over, 4))

#             # Apply vig of 9%
#             vig = Decimal("0.09")
#             vig_multiplier = Decimal("1") + vig

#             adjusted_over = implied_prob_over * vig_multiplier
#             adjusted_under = implied_prob_under * vig_multiplier

#             normalizer = adjusted_over + adjusted_under
#             prob_with_vig_over = sanitize_probability(adjusted_over / normalizer)
#             prob_with_vig_under = sanitize_probability(adjusted_under / normalizer)

#             # Convert to American odds
#             display_odds_over = decimal_prob_to_american(prob_with_vig_over)
#             display_odds_under = decimal_prob_to_american(prob_with_vig_under)

#             # Estimate implied probabilities
#             # implied_prob_over = sanitize_probability(estimate_implied_probability(bid, ask))
#             # implied_prob_under = sanitize_probability(round(Decimal("1.0") - implied_prob_over, 4))

#             # # Convert to American odds
#             # display_odds_over = decimal_prob_to_american(implied_prob_over)
#             # display_odds_under = decimal_prob_to_american(implied_prob_under)

#             if not over_exists:
#                 Market.objects.get_or_create(
#                     stock=stock,
#                     target_price=strike_price,
#                     expiry_date=expiry_date,
#                     outcome_type="over",
#                     defaults={
#                         "implied_odds_over": implied_prob_over,
#                         "implied_odds_under": Decimal("0"),
#                         "display_odds_over": display_odds_over,
#                         "is_active": True,
#                     },
#                 )
#                 created_count += 1

#             if not under_exists:
#                 Market.objects.get_or_create(
#                     stock=stock,
#                     target_price=strike_price,
#                     expiry_date=expiry_date,
#                     outcome_type="under",
#                     defaults={
#                         "implied_odds_over": Decimal("0"),
#                         "implied_odds_under": implied_prob_under,
#                         "display_odds_under": display_odds_under,
#                         "is_active": True,
#                     },
#                 )
#                 created_count += 1

#         except Exception as e:
#             print(f"❌ Error creating market for {stock_symbol} strike {option.get('strike')}: {e}")

#     print(f"✅ Created {created_count} new markets for {stock_symbol}, skipped {skipped_count}")

