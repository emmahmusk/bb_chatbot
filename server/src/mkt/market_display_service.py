

from datetime import date
from decimal import Decimal
import logging
from typing import Any, Dict, List
from .odds_transformer import OddsCalculator
from .polygon_data_fetcher import PolygonDataFetcher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MarketDisplayService:
    """
    Manages fetching data and calculating odds for multiple market listings
    to be displayed to users, grouped by expiry date.
    """
    def __init__(self, polygon_data_fetcher: PolygonDataFetcher, odds_calculator: OddsCalculator):
        self.polygon_data_fetcher = polygon_data_fetcher
        self.odds_calculator = odds_calculator

    def list_markets_by_expiry(self, expiry_date: date, stock_symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Generates a list of market listings for display based on a chosen expiry date.
        For simplicity, the target price for the over/under bet is set to the current stock price.
        """
        market_listings = []
        for symbol in stock_symbols:
            logger.info(f"Processing market for {symbol} with expiry {expiry_date}")

            # Get current stock price to use as the target price for the over/under bet
            current_stock_price = self.polygon_data_fetcher.get_last_stock_price(symbol)
            if not current_stock_price:
                logger.warning(f"Could not get current stock price for {symbol}. Skipping market listing.")
                continue

            # Calculate over/under odds for the current stock price as the target
            odds_result = self.odds_calculator.get_over_under_odds(
                polygon_data_fetcher=self.polygon_data_fetcher,
                stock_symbol=symbol,
                target_price=current_stock_price, # Use current price as target for display list
                expiry_date=expiry_date
            )

            if odds_result.get("over_odds") is not None and odds_result.get("under_odds") is not None:
                market_listings.append({
                    "stock_symbol": symbol,
                    "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                    "current_price": current_stock_price.quantize(Decimal("0.01")),
                    "target_price": current_stock_price.quantize(Decimal("0.01")),
                    "over_odds": odds_result["over_odds"],
                    "under_odds": odds_result["under_odds"],
                    "over_implied_probability_vig_adjusted": odds_result["over_implied_probability_vig_adjusted"].quantize(Decimal("0.0001")),
                    "under_implied_probability_vig_adjusted": odds_result["under_implied_probability_vig_adjusted"].quantize(Decimal("0.0001")),
                })
            else:
                logger.warning(f"Could not calculate odds for {symbol} with expiry {expiry_date}. Skipping market listing.")

        return market_listings