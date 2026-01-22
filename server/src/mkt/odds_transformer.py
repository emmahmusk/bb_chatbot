import logging
import math
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any, Union
from scipy.stats import norm

from .polygon_data_fetcher import PolygonDataFetcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
class OddsCalculator:
    """
    Handles all market odds calculations, including implied probability,
    vig adjustment, and odds format conversions.
    """
    def __init__(self, vig: Union[Decimal, float] = Decimal('0.10'),
                 risk_free_rate: Union[Decimal, float] = Decimal('0.02')):
        self._vig: Decimal = Decimal(str(vig))
        self._risk_free_rate: Decimal = Decimal(str(risk_free_rate))

    @property
    def vig(self) -> Decimal:
        """Returns the current vig."""
        return self._vig

    @vig.setter
    def vig(self, value: Union[Decimal, float]):
        """Sets the vig. This would be an admin-only function."""
        if not isinstance(value, (Decimal, float)) or value < 0:
            raise ValueError("Vig must be a non-negative Decimal or float.")
        self._vig = Decimal(str(value))
        logger.info(f"Vig set to: {self._vig}")

    @property
    def risk_free_rate(self) -> Decimal:
        """Returns the current risk-free rate."""
        return self._risk_free_rate

    @risk_free_rate.setter
    def risk_free_rate(self, value: Union[Decimal, float]):
        """Sets the risk-free rate. This would be an admin-only function."""
        if not isinstance(value, (Decimal, float)) or value < 0:
            raise ValueError("Risk-free rate must be a non-negative Decimal or float.")
        self._risk_free_rate = Decimal(str(value))
        logger.info(f"Risk-free rate set to: {self._risk_free_rate}")

    def implied_volatility_solver(self, market_price: Decimal, opt_type: str, S: Decimal, K_iv: Decimal, t: Decimal, r: Decimal, q: Decimal) -> Optional[Decimal]:
        """
        Placeholder for a real implied volatility solver.
        In a real application, this would use a numerical method (e.g., Newton-Raphson)
        to find the IV that makes the Black-Scholes price equal the market_price.
        For demonstration, returning a dummy IV.
        """
        logger.warning("Using dummy `implied_volatility_solver`. Replace with a real Black-Scholes IV solver.")
        # Dummy IV: A constant value or simple heuristic for demonstration.
        # This will need to be replaced with a proper iterative solver (e.g., Newton's method).
        # A common starting point for IV is around 0.20-0.30 for equity options.
        if t <= 0:
            return None # Cannot calculate IV for zero or negative time to expiry

        # Very simplistic logic to avoid common errors but not actually solving
        if S <= 0 or K_iv <= 0 or market_price <= 0:
            return None

        # Return a non-zero dummy value to allow calculation to proceed
        return Decimal('0.25') # Example constant IV for now


    def _calculate_implied_probability_for_market_outcome(
        self,
        market_data: Dict[str, Any],
        target_price: Decimal,
        outcome_type: str,  # 'over' or 'under'
    ) -> Optional[Decimal]:
        S = market_data.get("current_stock_price")
        t = market_data.get("time_to_expiry_years")
        calls_data = market_data.get("calls_data", [])
        puts_data = market_data.get("puts_data", [])
        r = market_data.get("risk_free_rate")
        q = market_data.get("dividend_yield", Decimal("0.00")) # Default to 0.00 if not provided
        
        print(f"Calculating implied probability for target price {target_price} with outcome type '{outcome_type}'")
        print(f"Current Stock Price (S): {S}, Time to Expiry (t): {t}, Risk-Free Rate (r): {r}, Dividend Yield (q): {q}")
        print(f"Calls Data: {calls_data}")
        print(f"Puts Data: {puts_data}")

        if not all([S is not None, t is not None, r is not None]):
            logger.error("Missing fundamental data (current_stock_price, time_to_expiry_years, risk_free_rate) for implied probability calculation.")
            return None
        
        if not (calls_data or puts_data) or t <= 0:
            logger.warning("No valid options data or time to expiry <= 0. Cannot calculate implied probability.")
            return None

        all_options = []
        if calls_data:
            # Ensure 'mid_price' exists and is not None before extending
            all_options.extend([{"type": "c", **opt} for opt in calls_data if opt.get("mid_price") is not None])
        if puts_data:
            # Ensure 'mid_price' exists and is not None before extending
            all_options.extend([{"type": "p", **opt} for opt in puts_data if opt.get("mid_price") is not None])
        
        if not all_options:
            logger.warning("No valid ATM options (with mid_price) for IV derivation.")
            return None
        
        # Sort by absolute difference to current stock price to find ATM option
        all_options.sort(key=lambda x: abs(x["strike"] - S))
        atm_option = all_options[0]

        K_iv = atm_option["strike"]
        market_price = atm_option["mid_price"]
        opt_type = atm_option["type"]

        # Call the implied volatility solver
        iv = self.implied_volatility_solver(market_price, opt_type, S, K_iv, t, r, q)

        if iv is None or iv <= 0: # Ensure IV is a positive value
            logger.warning("Could not calculate reliable or positive Implied Volatility. Skipping implied odds.")
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
            # Check for zero denominator before division
            if sigma_f * math.sqrt(t_f) <= 1e-9: # Use a small epsilon to check for near-zero
                logger.warning(f"Denominator (sigma * sqrt(t)) is zero or near-zero ({sigma_f * math.sqrt(t_f):.10f}) in d1/d2 calculation. Returning 0 probability.")
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
            
            # Clamp probability to a valid range to avoid extreme values
            implied_prob = max(Decimal("0.0001"), min(Decimal("0.9999"), implied_prob))
            return implied_prob.quantize(Decimal("0.0001"))

        except Exception as e:
            logger.error(f"Error in implied probability calculation: {e}", exc_info=True)
            return None

    def probability_to_american_odds(self, probability: Decimal) -> Decimal:
        """
        Converts a probability (0-1) to American odds.
        Positive odds for underdog (e.g., +150 for P=0.4), negative for favorite (e.g., -200 for P=0.66).
        """
        if not (0 < probability < 1):
            raise ValueError("Probability must be between 0 and 1 (exclusive).")

        if probability >= Decimal('0.5'):
            # Favorite (negative odds)
            odds = (probability / (1 - probability)) * -100
        else:
            # Underdog (positive odds)
            odds = ((1 - probability) / probability) * 100
        return odds.quantize(Decimal('0.01'))

    def probability_to_decimal_odds(self, probability: Decimal) -> Decimal:
        """
        Converts a probability (0-1) to Decimal odds.
        """
        if not (0 < probability <= 1):
            raise ValueError("Probability must be between 0 and 1 (exclusive for strict conversion, inclusive for 1 for guaranteed wins).")
        return (Decimal('1') / probability).quantize(Decimal('0.01'))

    def probability_to_fractional_odds(self, probability: Decimal) -> str:
        """
        Converts a probability (0-1) to Fractional odds (e.g., 5/1).
        """
        if not (0 < probability < 1):
            raise ValueError("Probability must be between 0 and 1 (exclusive).")
        decimal_odds = self.probability_to_decimal_odds(probability)
        if decimal_odds <= 1: # Represents a guaranteed win, which doesn't fit standard fractional odds
            return "0/1"
        num = decimal_odds - 1
        # Find a common denominator to express as a simple fraction
        # This is a simplification; a proper fraction simplification algorithm would be better
        # For now, let's just make it simple if possible, otherwise use a high denominator.
        for denominator in range(1, 101): # Check up to denominator 100
            numerator = num * denominator
            if numerator == int(numerator):
                return f"{int(numerator)}/{denominator}"
        # Fallback for complex decimals: use a large denominator
        return f"{int(num * 100)}/100" # e.g. 1.5 -> 150/100 -> 3/2

    def adjust_odds_with_vig(self, raw_probability: Decimal, market_side: str) -> Decimal:
        """
        Adjusts raw implied probability to incorporate the vig.
        This is a simplified representation of vig application.
        The vig typically skews the true odds in favor of the house.
        For a two-sided bet, the sum of implied probabilities (from offered odds) will exceed 1.
        
        Args:
            raw_probability (Decimal): The probability derived from the market.
            market_side (str): 'over' or 'under' to determine how vig is applied.
        """
        vig_as_decimal = self._vig # Assuming vig is like 0.10 for 10 cents
        
        # This is a simple approximation:
        adjusted_probability = raw_probability * (1 + self._vig)
        if adjusted_probability > Decimal('0.99'): # Cap at reasonable max
            adjusted_probability = Decimal('0.99')
        return adjusted_probability

    def get_over_under_odds(
        self,
        polygon_data_fetcher: PolygonDataFetcher,
        stock_symbol: str,
        target_price: Decimal,
        expiry_date: date,
        dividend_yield: Decimal = Decimal('0.00') # Added dividend_yield as an argument
    ) -> Dict[str, Any]:
        """
        Calculates the 'over' and 'under' odds for a stock price target by a set date
        by preparing market_data and calling the core calculation function.
        """
        market_data = {}

        # 1. Get current stock price
        current_price = polygon_data_fetcher.get_last_stock_price(stock_symbol)
        if not current_price:
            logger.error(f"Could not get current price for {stock_symbol}. Cannot calculate odds.")
            return {"over_odds": None, "under_odds": None}
        market_data["current_stock_price"] = current_price

        # 2. Calculate time to expiration
        time_to_expiration_days = (expiry_date - date.today()).days
        if time_to_expiration_days <= 0:
            logger.error("Expiry date must be in the future. Cannot calculate odds.")
            return {"over_odds": None, "under_odds": None}
        time_to_expiration_years = Decimal(str(time_to_expiration_days / 365.25))
        market_data["time_to_expiry_years"] = time_to_expiration_years

        market_data["risk_free_rate"] = self._risk_free_rate
        market_data["dividend_yield"] = dividend_yield

        # 3. Fetch all relevant option contracts
        all_contracts = polygon_data_fetcher.get_option_contracts(
            underlying_ticker=stock_symbol,
            expiration_date=expiry_date.strftime("%Y-%m-%d")
        )

        calls_data = []
        puts_data = []

        # 4. Process each contract to get mid_price and structure data
        for contract in all_contracts:
            option_ticker = contract.get('ticker')
            contract_type = contract.get('contract_type')
            strike_price = Decimal(str(contract.get('strike_price')))

            if option_ticker and (contract_type == 'call' or contract_type == 'put'):
                quote = polygon_data_fetcher.get_option_quote(option_ticker)
                if quote:
                    # Use .get() with default 0 to handle missing keys safely
                    bid = Decimal(str(quote.get('bid_price', 0)))
                    ask = Decimal(str(quote.get('ask_price', 0)))
                    
                    logger.debug(f"Quote for {option_ticker}: Bid={bid}, Ask={ask}") # Add this line
                    # Only calculate mid_price if both bid and ask are positive (valid quote)
                    if bid > 0 and ask > 0:
                        mid_price = (bid + ask) / 2
                        option_info = {
                            "ticker": option_ticker,
                            "strike": strike_price,
                            "mid_price": mid_price,
                            "bid_price": bid,
                            "ask_price": ask,
                            "contract_type": contract_type # Add contract_type for easier debugging
                        }
                        if contract_type == 'call':
                            calls_data.append(option_info)
                        elif contract_type == 'put':
                            puts_data.append(option_info)
                        logger.info(f"Raw contracts fetched for {stock_symbol} ({expiry_date}): {len(all_contracts)}")
                        logger.info(f"Processed Calls Data for {stock_symbol}: {len(calls_data)} entries")
                        logger.info(f"Processed Puts Data for {stock_symbol}: {len(puts_data)} entries")
                    else:
                        logger.debug(f"Skipping option {option_ticker} due to invalid bid/ask prices (bid: {bid}, ask: {ask}).")
                else:
                    logger.debug(f"Could not get quote for option {option_ticker}.")
            else:
                logger.debug(f"Skipping invalid or incomplete contract data: {contract}")

        market_data["calls_data"] = calls_data
        market_data["puts_data"] = puts_data

        # 5. Call the core implied probability calculation function with the structured market_data
        over_implied_prob = self._calculate_implied_probability_for_market_outcome(
            market_data=market_data,
            target_price=target_price,
            outcome_type='over'
        )

        under_implied_prob = self._calculate_implied_probability_for_market_outcome(
            market_data=market_data,
            target_price=target_price,
            outcome_type='under'
        )

        if over_implied_prob is None or under_implied_prob is None:
            logger.error("Implied probability calculation failed for 'over' or 'under' outcome after processing.")
            return {"over_odds": None, "under_odds": None}

        # 6. Apply vig and convert to odds
        over_prob_with_vig = self.adjust_odds_with_vig(over_implied_prob, 'over')
        under_prob_with_vig = self.adjust_odds_with_vig(under_implied_prob, 'under')

        over_odds = self.probability_to_american_odds(over_prob_with_vig)
        under_odds = self.probability_to_american_odds(under_prob_with_vig)
        
        return {
            "over_odds": over_odds,
            "under_odds": under_odds,
            "over_implied_probability_raw": over_implied_prob,
            "under_implied_probability_raw": under_implied_prob,
            "over_implied_probability_vig_adjusted": over_prob_with_vig,
            "under_implied_probability_vig_adjusted": under_prob_with_vig,
            "vig_applied": self.vig,
            "risk_free_rate_used": self.risk_free_rate,
            "market_data_for_debug": market_data # Optional: include for debugging
        }