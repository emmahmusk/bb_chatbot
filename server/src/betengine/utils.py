# betengine/utils.py

from datetime import date
import logging
import math
from decimal import Decimal, InvalidOperation, getcontext, ROUND_HALF_UP
from typing import Optional, Union
from fractions import Fraction
from scipy.optimize import newton  # For implied volatility solver
# For Black-Scholes and implied volatility (requires pip install scipy)
from scipy.stats import norm
from functools import lru_cache
from django.db.models import Sum, Q, F
from django.db.models.functions import Coalesce
from typing import Union, Iterable, Dict, List


# def _compute_balanced_probs(self, base_over: Decimal, base_under: Decimal, over_nudge: int, under_nudge: int) -> tuple[Decimal, Decimal]:
#         """
#         Computes balanced over/under probabilities ensuring they always sum to 1.00.
#         Nudges are interpreted as integer percent shifts (±n).
#         """
#         # Base in percentage
#         over_percent = float(base_over) * 100
#         under_percent = float(base_under) * 100

#         # Apply offsets symmetrically
#         total_nudge = over_nudge - under_nudge  # net shift toward over side
#         new_over_percent = over_percent + total_nudge
#         new_over_percent = max(1, min(new_over_percent, 99))
#         new_under_percent = 100 - new_over_percent

#         return (
#             Decimal(str(new_over_percent / 100)).quantize(Decimal("0.0001")),
#             Decimal(str(new_under_percent / 100)).quantize(Decimal("0.0001")),
#         )

logger = logging.getLogger(__name__)
getcontext().prec = 10  # Set Decimal precision for calculationss

# ... (Include your existing functions like black_scholes_price,
#      implied_volatility_solver, calculate_implied_probability_for_market_outcome,
#      convert_decimal_to_american_odds, apply_vig, etc.) ...


def calculate_payout(amount_wagered: Decimal, american_odds: str) -> Decimal:
    """
    Calculates the total potential payout (wager + winnings) from a given
    amount wagered and American odds.

    Args:
        amount_wagered (Decimal): The amount of money placed on the bet.
        american_odds (str): The American odds string (e.g., "+150", "-200").

    Returns:
        Decimal: The total potential payout (wager + winnings).
                 Returns 0 if odds are invalid or calculation fails.
    """
    try:
        wager = Decimal(str(amount_wagered))
        odds_val = Decimal(american_odds)

        if odds_val == 0:  # Odds of 0 don't make sense in American format
            return Decimal("0.00")

        if odds_val > 0:  # Positive odds (e.g., +150)
            # For every $100 wagered, you win $odds_val.
            winnings = wager * (odds_val / Decimal("100"))
        else:  # Negative odds (e.g., -200)
            # You must wager $abs(odds_val) to win $100.
            winnings = wager / (abs(odds_val) / Decimal("100"))
        return (wager + winnings).quantize(
            Decimal("0.01")
        )  # Round to two decimal places
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.error(
            f"Error calculating payout for wager={amount_wagered}, odds={american_odds}: {e}"
        )
        return Decimal("0.00")  # Return 0 for invalid calculations


# --- Core Black-Scholes Option Pricing Function ---
def black_scholes_price(
    option_type: str,  # 'c' for call, 'p' for put
    S: Decimal,  # Current stock price
    K: Decimal,  # Strike price
    t: Decimal,  # Time to expiry in years
    r: Decimal,  # Risk-free rate
    sigma: Decimal,  # Volatility (implied volatility)
    q: Decimal = Decimal("0.00"),  # Dividend yield (default 0)
) -> Decimal:
    """
    Calculates Black-Scholes option price.
    """
    if t <= 0:  # Option should have some time to expiry
        return Decimal("0")

    # Convert to float for math operations that don't support Decimal directly
    # and for scipy.stats.norm functions. Convert back to Decimal at the end.
    S_f, K_f, t_f, r_f, sigma_f, q_f = (
        float(S),
        float(K),
        float(t),
        float(r),
        float(sigma),
        float(q),
    )

    # Avoid division by zero or log(0) if sigma or t are extremely small
    if sigma_f <= 1e-9 or t_f <= 1e-9:  # Very small values
        return Decimal("0")

    sqrt_t = math.sqrt(t_f)
    sigma_sqrt_t = sigma_f * sqrt_t

    d1 = (math.log(S_f / K_f) + (r_f - q_f + 0.5 * sigma_f**2) * t_f) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t

    try:
        if option_type == "c":
            price = S_f * math.exp(-q_f * t_f) * norm.cdf(d1) - K_f * math.exp(
                -r_f * t_f
            ) * norm.cdf(d2)
        elif option_type == "p":
            price = K_f * math.exp(-r_f * t_f) * norm.cdf(-d2) - S_f * math.exp(
                -q_f * t_f
            ) * norm.cdf(-d1)
        else:
            raise ValueError("Option type must be 'c' (call) or 'p' (put).")

        # Ensure price is not negative due to floating point inaccuracies at very low values
        return Decimal(str(max(0.0, price)))
    except OverflowError:
        logger.error(
            f"OverflowError in Black-Scholes price calculation for S={S}, K={K}, t={t}, r={r}, sigma={sigma}, q={q}"
        )
        return Decimal("0")  # Return 0 or handle as appropriate for extreme inputs
    except Exception as e:
        logger.error(f"Error in Black-Scholes price calculation: {e}", exc_info=True)
        return Decimal("0")  # Default return on error


# --- Implied Volatility (IV) Solver ---
def implied_volatility_solver(
    market_price: Decimal,  # The option's market price (mid_price)
    option_type: str,
    S: Decimal,
    K: Decimal,
    t: Decimal,
    r: Decimal,
    q: Decimal = Decimal("0.00"),
    initial_guess: Decimal = Decimal("0.50"),  # Common initial guess for IV
) -> Optional[Decimal]:
    """
    Calculates implied volatility using Newton-Raphson method.
    """
    if (
        market_price <= 0 or t <= 0
    ):  # IV cannot be derived for zero/negative price or zero time
        return Decimal("0")

    # Define the function whose root we want to find: f(sigma) = calculated_price(sigma) - market_price
    def f(sigma_float):
        # Ensure sigma_float is positive for Black-Scholes
        sigma_val = Decimal(
            str(max(1e-9, sigma_float))
        )  # Ensure sigma is slightly positive
        calculated_price = black_scholes_price(option_type, S, K, t, r, sigma_val, q)
        return float(calculated_price - market_price)

    # Define the vega (derivative of price with respect to volatility) for Newton's method
    def vega(sigma_float):
        # Ensure sigma_float is positive
        sigma_val = Decimal(str(max(1e-9, sigma_float)))
        t_f = float(t)
        if t_f <= 1e-9 or sigma_val <= 1e-9:
            return 1e-9  # Prevent division by zero if t or sigma are tiny

        d1 = (
            math.log(float(S / K))
            + (float(r) - float(q) + 0.5 * float(sigma_val) ** 2) * t_f
        ) / (float(sigma_val) * math.sqrt(t_f))
        vega_val = float(S) * math.exp(-float(q) * t_f) * norm.pdf(d1) * math.sqrt(t_f)
        return max(1e-9, vega_val)  # Ensure vega is positive for convergence

    try:
        # Use scipy's newton method to find the root (implied volatility)
        # Ensure initial_guess is a float for newton
        # Add bounds to the search to keep IV within a reasonable range (e.g., 1% to 500%)
        iv_float = newton(f, float(initial_guess), fprime=vega, tol=1e-6, maxiter=100)

        # Validate the result: IV should be positive and within a reasonable range (e.g., 0.01 to 5.0)
        if 0.01 <= iv_float <= 5.0:  # Volatility typically between 1% and 500%
            return Decimal(str(iv_float))
        else:
            logger.warning(
                f"Implied volatility {iv_float:.4f} out of reasonable range [0.01, 5.0]. S={S}, K={K}, t={t}, price={market_price}, type={option_type}"
            )
            return None  # IV not found or unreasonable
    except RuntimeError as e:  # newton raises RuntimeError if it doesn't converge
        logger.warning(
            f"Implied volatility solver failed to converge for market_price={market_price}, S={S}, K={K}, t={t}, type={option_type}: {e}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error in IV solver for market_price={market_price}, S={S}, K={K}, t={t}, type={option_type}: {e}",
            exc_info=True,
        )
        return None


# --- Odds Transformation Functions ---
def prob_to_american(prob: float) -> str:
    """
    Convert a probability (between 0 and 1) to American odds.
    Clamps extremely low/high probs to avoid +100000/-100000 values.
    """
    prob = max(0.001, min(prob, 0.999))  # Clamp between 0.1% and 99.9%
    
    if prob == 0.5:
        return "+100"
    elif prob < 0.5:
        return f"+{int((100 * (1 - prob)) / prob)}"
    else:
        return f"-{int((100 * prob) / (1 - prob))}"
    
def implied_probability_to_american(prob):
    if prob <= 0 or prob >= 1:
        return None
    if prob > 0.5:
        return str(round(-100 * prob / (1 - prob)))
    else:
        return f"+{round(100 * (1 - prob) / prob)}"


def convert_decimal_to_american_odds(probability: Decimal) -> Optional[str]:
    """Converts a decimal probability (0-1) to American odds string."""
    if not (
        Decimal("0.0001") <= probability <= Decimal("0.9999")
    ):  # Probabilities must be within this range
        logger.warning(
            f"Invalid probability for American odds conversion: {probability}"
        )
        return None  # Return None or raise error for invalid input

    if probability >= Decimal("0.50"):
        # Negative odds (e.g., -110)
        # Formula: -(probability / (1 - probability)) * 100
        odds = (probability / (Decimal("1.00") - probability)) * Decimal("100.00")
        return f"-{odds.quantize(Decimal('1'))}"
    else:
        # Positive odds (e.g., +150)
        # Formula: ((1 - probability) / probability) * 100
        odds = ((Decimal("1.00") - probability) / probability) * Decimal("100.00")
        return f"+{odds.quantize(Decimal('1'))}"


def apply_vig(over_prob: float, under_prob: float, target_margin: float = 0.09) -> tuple:
    """
    Scales probabilities so their sum equals (1 + margin).
    """
    total = over_prob + under_prob
    if total == 0:
        return 0.5, 0.5
    scaling = (1 + target_margin) / total
    return over_prob * scaling, under_prob * scaling


def american_to_decimal_odds(american_odds: str) -> Optional[Decimal]:
    """Converts American odds string to decimal odds."""
    try:
        american = Decimal(american_odds)
    except (ValueError, TypeError):
        logger.error(f"Invalid American odds string: {american_odds}")
        return None

    if american > 0:
        return (american / Decimal("100")) + Decimal("1")
    elif american < 0:
        return (Decimal("100") / abs(american)) + Decimal("1")
    else:  # Odds of 0 are not standard in American format (can imply infinite probability)
        logger.warning(f"American odds of 0 encountered: {american_odds}")
        return None


def decimal_to_implied_probability(decimal_odds: Decimal) -> Optional[Decimal]:
    """Converts decimal odds to implied probability."""
    if decimal_odds <= 0:
        logger.warning(f"Decimal odds must be positive: {decimal_odds}")
        return None
    return (Decimal("1") / decimal_odds).quantize(Decimal("0.0001"))

def american_to_decimal_odds(american_odds: Union[str, int, float, Decimal]) -> Optional[Decimal]:
    """
    Converts American odds to Decimal odds.
    Examples:
        +150 → 2.50
        -200 → 1.50
    """
    try:
        american = Decimal(str(american_odds))
    except (InvalidOperation, TypeError):
        return None

    if american > 0:
        decimal_odds = (american / Decimal("100")) + Decimal("1")
    elif american < 0:
        decimal_odds = (Decimal("100") / abs(american)) + Decimal("1")
    else:
        return None

    # Round to 2 decimal places for presentation consistency
    return decimal_odds.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def decimal_to_american_odds(decimal_odds: Union[str, Decimal, float]) -> Optional[Decimal]:
    """
    Converts Decimal odds back to American odds.
    Examples:
        2.50 → +150
        1.50 → -200
    """
    try:
        dec = Decimal(str(decimal_odds))
    except (InvalidOperation, TypeError):
        return None

    if dec < 1:
        return None

    if dec >= 2:
        american = (dec - Decimal("1")) * Decimal("100")
    else:
        american = (-100) / (dec - Decimal("1"))

    return american.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def decimal_to_fractional_odds(decimal_odds: Union[str, Decimal, float]) -> Optional[str]:
    """
    Converts Decimal odds to Fractional format.
    Example:
        2.50 → "3/2"
        1.50 → "1/2"
    """
    try:
        dec = Decimal(str(decimal_odds))
    except (InvalidOperation, TypeError):
        return None

    if dec <= 1:
        return "0/1"

    frac = Fraction(dec - 1).limit_denominator(100)
    return f"{frac.numerator}/{frac.denominator}"


def american_to_fractional_odds(american_odds: Union[str, int, float, Decimal]) -> Optional[str]:
    """
    Converts American odds to Fractional odds.
    Example:
        +150 → "3/2"
        -200 → "1/2"
    """
    decimal_odds = american_to_decimal_odds(american_odds)
    return decimal_to_fractional_odds(decimal_odds) if decimal_odds else None


def fractional_to_decimal_odds(fractional_odds: str) -> Optional[Decimal]:
    """
    Converts Fractional odds (e.g., "3/2") to Decimal odds.
    Example:
        "3/2" → 2.50
    """
    try:
        num, denom = fractional_odds.split("/")
        frac = Decimal(num) / Decimal(denom)
        return (frac + Decimal("1")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None

@lru_cache(maxsize=512)
def convert_odds(odds: Union[str, int, float, Decimal], to_format: str = "american") -> Optional[Union[str, Decimal]]:
    """
    Converts odds between American, Decimal, and Fractional formats using cached results.
    Default base format is American.
    """
    if odds is None:
        return None

    to_format = (to_format or "american").lower()

    # --- Detect base odds type ---
    odds_str = str(odds).strip()
    base_format = "fractional" if "/" in odds_str else "american"  # default assume american

    try:
        # --- Convert to Decimal as the pivot format ---
        if base_format == "american":
            decimal_value = american_to_decimal_odds(odds)
        elif base_format == "fractional":
            decimal_value = fractional_to_decimal_odds(odds)
        else:
            decimal_value = Decimal(str(odds))

        if decimal_value is None:
            return None

        # --- Convert to target format ---
        if to_format == "american":
            return decimal_to_american_odds(decimal_value)
        elif to_format == "decimal":
            return decimal_value
        elif to_format == "fractional":
            return decimal_to_fractional_odds(decimal_value)

        # Default return (fallback)
        return decimal_to_american_odds(decimal_value)
    except Exception:
        return None

def populate_market_from_option_data(
    stock,
    target_price: float,
    expiry_date: date,
    option_data: dict,
    market_model,
    target_margin: float = 0.09,
):
    """
    Creates or updates a Market instance from Alpha Vantage option data.
    """
    bid = float(option_data.get("bid", 0))
    ask = float(option_data.get("ask", 0))
    mid_price = (bid + ask) / 2 if bid and ask else float(option_data.get("mark", 0))

    if not mid_price:
        return None  # skip invalid data

    strike = float(option_data.get("strike_price", target_price))
    delta = float(option_data.get("delta", 0.5))  # fallback if missing

    # Step 1: Estimate raw implied probabilities
    prob_over = delta
    prob_under = 1 - prob_over

    # Step 2: Apply vig/margin
    adj_over, adj_under = apply_vig(prob_over, prob_under, target_margin)

    # Step 3: Convert to American odds
    odds_over = prob_to_american(adj_over)
    odds_under = prob_to_american(adj_under)

    # Step 4: Update or create market
    market, created = market_model.objects.update_or_create(
        stock=stock,
        target_price=Decimal(str(strike)),
        expiry_date=expiry_date,
        outcome_type="over",
        defaults={
            "implied_odds_over": Decimal(str(prob_over)),
            "implied_odds_under": Decimal(str(prob_under)),
            "display_odds_over": odds_over,
            "display_odds_under": odds_under,
            "is_active": True,
        },
    )

    return market
VIG_KEY = "vig_9_0_percent"

def nudge_odds_ladder(
    current_br_true_percent: Decimal,
    nudge_direction: int,
    odds_ladder: list,
    vig_key: str = "vig_9_0_percent"
) -> dict | None:
    """
    Moves odds up or down the ladder while keeping the vig constant.
    Detects which side (over/under) the current percent matches and
    stays on that side when stepping through the ladder.
    """

    if not odds_ladder:
        print("⚠️ Error: Empty odds ladder provided.")
        return None

    try:
        current_percent = round(float(current_br_true_percent), 2)
    except Exception as e:
        print(f"⚠️ Invalid current_br_true_percent: {current_br_true_percent} ({e})")
        return None

    # --- 1️⃣ Find closest match and which side it belongs to ---
    closest_index = None
    side_matched = None
    min_diff = float("inf")

    for i, row in enumerate(odds_ladder):
        try:
            over_p = round(float(row.get("br_true_percent", 0)), 2)
            under_p = round(float(row.get("br_true_percent_opposite", 0)), 2)
        except Exception:
            continue

        diff_over = abs(over_p - current_percent)
        diff_under = abs(under_p - current_percent)

        if diff_over < min_diff:
            min_diff = diff_over
            closest_index = i
            side_matched = "over"
        if diff_under < min_diff:
            min_diff = diff_under
            closest_index = i
            side_matched = "under"

    if closest_index is None:
        print(f"⚠️ Could not locate nearest ladder index for {current_percent}")
        return None

    # --- 2️⃣ Compute new index based on direction ---
    step = 1 if nudge_direction > 0 else -1
    target_index = closest_index + step

    if target_index < 0 or target_index >= len(odds_ladder):
        print("⚠️ Edge of ladder reached.")
        return None

    target_row = odds_ladder[target_index]
    if vig_key not in target_row:
        print(f"⚠️ Missing vig key '{vig_key}' at index {target_index}")
        return None

    # --- 3️⃣ Stay on matched side ---
    if side_matched == "over":
        br_true_percent = Decimal(str(target_row["br_true_percent"]))
        br_true_percent_opposite = Decimal(str(target_row["br_true_percent_opposite"]))
    else:
        br_true_percent = Decimal(str(target_row["br_true_percent_opposite"]))
        br_true_percent_opposite = Decimal(str(target_row["br_true_percent"]))

    # --- 4️⃣ Prepare result ---
    result = {
        "previous_index": closest_index,
        "new_index": target_index,
        "matched_side": side_matched,
        "br_true_percent": br_true_percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "br_true_percent_opposite": br_true_percent_opposite.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "american_odds": target_row[vig_key],
    }

    print(
        f"Nudge ({side_matched}) {current_percent} → {result['br_true_percent']} | "
        f"Direction: {'UP' if nudge_direction > 0 else 'DOWN'} | "
        f"Index {closest_index} → {target_index}"
    )

    return result

def find_nearest_ladder_index(br_true_percent, odds_ladder):
    """
    Return the ladder index whose br_true_percent equals br_true_percent,
    or the nearest index if not exact match (nearest by absolute diff).
    Returns index or None if ladder empty.
    """
    if not odds_ladder:
        return None

    # Normalize to Decimal for safe comparison
    try:
        target = Decimal(str(br_true_percent))
    except Exception:
        return None

    nearest_index = None
    nearest_diff = None
    for i, row in enumerate(odds_ladder):
        try:
            row_pct = Decimal(str(row.get("br_true_percent")))
        except Exception:
            continue
        diff = abs(row_pct - target)
        if nearest_diff is None or diff < nearest_diff:
            nearest_diff = diff
            nearest_index = i
        if diff == 0:
            break
    return nearest_index


def _walk_ladder_steps(start_index: int, steps: int, odds_ladder: list, vig_key: str = "vig_9_0_percent"):
    """
    Walk `steps` steps from start_index on odds_ladder.
    steps may be positive (up) or negative (down). Returns final row dict or None if edge reached.
    """
    if start_index is None or not odds_ladder:
        return None

    idx = start_index
    step_dir = 1 if steps > 0 else -1 if steps < 0 else 0
    for _ in range(abs(steps)):
        next_idx = idx + step_dir
        if next_idx < 0 or next_idx >= len(odds_ladder):
            return None
        idx = next_idx
    final_row = odds_ladder[idx]
    # ensure vig_key exists; if not, final_row still returned but caller will handle fallback
    return {"index": idx, **final_row}

def calculate_user_wager_exposure(users, base_limit=Decimal("500.00")):
    """
    Calculates CRS exposure for each user.
    CRS Exposure = total_wagered / base_limit.
    
    Uses the correct related names from Bet and ParlayBet models.
    """

    if not isinstance(base_limit, Decimal):
        base_limit = Decimal(str(base_limit))

    if base_limit <= Decimal("0"):
        return [
            {"user_id": u.id, "username": getattr(u, "username", str(u)), "crs_exposure": Decimal("1.00")}
            for u in users
        ]

    # Annotate each user with sums from bets and parlay_bets
    users_with_wagers = users.annotate(
        wagered_single=Coalesce(
            Sum(
                "bets__amount_wagered",
                filter=Q(bets__is_parlay_leg=False) & Q(bets__status__in=["pending", "won", "lost", "void"]),
                default=Decimal("0.00")
            ),
            Decimal("0.00")
        ),
        wagered_parlay=Coalesce(
            Sum(
                "parlay_bets__amount_wagered",
                filter=Q(parlay_bets__status__in=["pending", "won", "lost", "void"]),
                default=Decimal("0.00")
            ),
            Decimal("0.00")
        )
    ).values("id", "username", "wagered_single", "wagered_parlay")

    results = []
    for u in users_with_wagers:
        total_wagered = (u["wagered_single"] or Decimal("0.00")) + (u["wagered_parlay"] or Decimal("0.00"))
        crs_exposure = (total_wagered / base_limit).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        results.append({
            "user_id": u["id"],
            "username": u.get("username"),
            "total_wagered": total_wagered,
            "crs_exposure": crs_exposure,
        })

    return results


# def nudge_odds_ladder(
#     current_br_true_percent: int, 
#     nudge_direction: int, 
#     odds_ladder: list, 
#     vig_key: str = "vig_9_0_percent"
# ) -> dict or None:
#     """
#     Nudges the odds (br_true_percent, br_true_percent_opposite, and American odds) 
#     up or down the ladder while keeping the vigorish fixed.

#     :param current_br_true_percent: The 'br_true_percent' of the current odds row.
#     :param nudge_direction: The direction of the nudge. 
#                             Positive (> 0) for up, negative (< 0) for down, 0 for no change.
#     :param odds_ladder: The list of odds objects (the ODDS_LADDER_JSON).
#     :param vig_key: The fixed vigorish key to use (e.g., 'vig_9_0_percent').
#     :return: The new odds object (dictionary) or None if an edge case is hit.
#     """
    
#     # 1. Find the current index
#     try:
#         current_index = next(
#             i for i, row in enumerate(odds_ladder) 
#             if row["br_true_percent"] == current_br_true_percent
#         )
#     except StopIteration:
#         # Edge Case 1: Current br_true_percent not found in the ladder
#         print(f"Error: br_true_percent {current_br_true_percent} not found in the odds ladder.")
#         return None

#     # 2. Determine the target index
#     # Positive nudge_direction moves up the list (higher index, higher br_true_percent)
#     # Negative nudge_direction moves down the list (lower index, lower br_true_percent)
#     target_index = current_index + (1 if nudge_direction > 0 else -1 if nudge_direction < 0 else 0)

#     # 3. Handle Edge Cases for Nudging
#     if target_index == current_index:
#         # Edge Case 2: No change requested (nudge_direction == 0)
#         # Return the current row (or None if you prefer to signal no change)
#         return odds_ladder[current_index]

#     if target_index < 0:
#         # Edge Case 3: Nudging down past the bottom (lowest br_true_percent)
#         print(f"Edge Case: Cannot nudge down past the lowest br_true_percent ({odds_ladder[0]['br_true_percent']}).")
#         return odds_ladder[0]  # Return the lowest possible row

#     if target_index >= len(odds_ladder):
#         # Edge Case 4: Nudging up past the top (highest br_true_percent)
#         last_index = len(odds_ladder) - 1
#         print(f"Edge Case: Cannot nudge up past the highest br_true_percent ({odds_ladder[last_index]['br_true_percent']}).")
#         return odds_ladder[last_index] # Return the highest possible row

#     # 4. Extract the new odds from the target index
#     new_odds_row = odds_ladder[target_index]
    
#     # 5. Build the final output structure, ensuring only the required fields are present
    
#     # Check if the requested vig key exists in the new row (should always be true based on your data structure)
#     if vig_key not in new_odds_row:
#         # Edge Case 5: The specified vig key is missing from the target row
#         print(f"Error: Vigorish key '{vig_key}' missing in the target odds row.")
#         return None

#     # The final output structure
#     result = {
#         "br_true_percent": new_odds_row["br_true_percent"],
#         "br_true_percent_opposite": new_odds_row["br_true_percent_opposite"],
#         "american_odds": new_odds_row[vig_key]
#     }

#     return result