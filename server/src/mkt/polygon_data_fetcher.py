import logging
import os
from datetime import date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from polygon.rest.models import LastTrade, LastQuote, MarketStatus
from polygon import RESTClient
from django.conf import settings

logger = logging.getLogger(__name__)


class PolygonDataFetcher:
    """Fetches live data from Polygon.io for market odds calculation."""

    def __init__(self, api_key: Optional[str] = None, client: Optional[RESTClient] = None):
        if client:
            self.client = client
        else:
            api_key = api_key or settings.POLYGON_API_KEY
            if not api_key:
                raise ValueError("A Polygon API key must be provided or set as POLYGON_API_KEY env var.")
            self.client = RESTClient(api_key)

    def get_last_stock_price(self, stock_symbol: str) -> Optional[Decimal]:
        """
        Fetch the last trade price for a given stock symbol.
        """
        try:
            resp: LastTrade = self.client.get_last_trade(stock_symbol)
            # The SDK may return an object or dict; handle both
            price = getattr(resp, "price", None) if not isinstance(resp, dict) else resp.get("price")
            if price is not None:
                return Decimal(str(price))
            logger.warning(f"No last trade price found for stock {stock_symbol}.")
        except Exception as e:
            logger.error(f"Error fetching last stock price for {stock_symbol}: {e}")
        return None

    def get_historical_stock_close(self, stock_symbol: str, query_date: date) -> Optional[Decimal]:
        """
        Fetch the closing price of a stock on a specific date (using daily open/close endpoint).
        """
        try:
            # Type hint removed as DailyOpenClose is not directly imported
            resp = self.client.get_daily_open_close(stock_symbol, query_date.strftime("%Y-%m-%d"))
            close = getattr(resp, "close", None) if not isinstance(resp, dict) else resp.get("close")
            if close is not None:
                return Decimal(str(close))
            logger.warning(f"No close price for {stock_symbol} on {query_date}.")
        except Exception as e:
            logger.error(f"Error fetching close price for {stock_symbol} on {query_date}: {e}")
        return None

    def get_option_contracts(
        self,
        underlying_ticker: str,
        strike_price: Optional[float] = None,
        expiration_date: Optional[str] = None,
        contract_type: Optional[str] = None, # 'call' or 'put'
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List option contracts for an underlying using /v3/reference/options/contracts.
        Filters on strike_price and expiration_date are applied after fetching.
        """
        try:
            contracts = []
            iterator = self.client.list_options_contracts(
                underlying_ticker=underlying_ticker,
                contract_type=contract_type,
            )
            for i, contract in enumerate(iterator):
                if limit and i >= limit:
                    break
                # Convert contract object to dict for consistent handling
                contract_dict = contract.__dict__ if hasattr(contract, "__dict__") else contract

                if strike_price is not None and contract_dict.get("strike_price") != strike_price:
                    continue
                if expiration_date is not None and contract_dict.get("expiration_date") != expiration_date:
                    continue
                contracts.append(contract_dict)
                logger.info(f"Fetched {len(contracts)} option contracts for {underlying_ticker} expiring on {expiration_date}")
            return contracts
        except Exception as e:
            logger.error(f"Error fetching option contracts for {underlying_ticker}: {e}")
            return []

    def get_option_quote(self, option_ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the latest NBBO quote for a given option ticker.
        """
        try:
            resp: LastQuote = self.client.get_option_last_quote(option_ticker)
            # The SDK may return an object or dict; handle both
            return resp.get("results") if isinstance(resp, dict) else getattr(resp, "results", None)
        except Exception as e:
            logger.error(f"Error fetching option quote for {option_ticker}: {e}")
            return None

    def get_option_last_trade(self, option_ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the last trade for a given option ticker.
        """
        try:
            resp: LastTrade = self.client.get_option_last_trade(option_ticker)
            return resp.get("results") if isinstance(resp, dict) else getattr(resp, "results", None)
        except Exception as e:
            logger.error(f"Error fetching option last trade for {option_ticker}: {e}")
            return None

    def get_options_snapshot(self, underlying_ticker: str, option_ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch an options chain snapshot for a given underlying and option contract.
        """
        try:
            resp = self.client.get_snapshot_option(underlying_ticker, option_ticker)
            return resp.get("results") if isinstance(resp, dict) else getattr(resp, "results", None)
        except Exception as e:
            logger.error(f"Error fetching options snapshot for {underlying_ticker} / {option_ticker}: {e}")
            return None

    def get_market_status(self) -> Optional[Dict[str, Any]]:
        """
        Fetch the current market status.
        """
        try:
            resp: MarketStatus = self.client.get_market_status()
            return resp.__dict__ if hasattr(resp, '__dict__') else resp
        except Exception as e:
            logger.error(f"Error fetching market status: {e}")
            return None

    def fetch_data_for_market_odds(
        self, stock_symbol: str, option_ticker: str, expiry: date
    ) -> Dict[str, Any]:
        """
        Aggregate all relevant data for updating market odds in one call.
        """
        return {
            "last_stock_price": self.get_last_stock_price(stock_symbol),
            "historical_close": self.get_historical_stock_close(stock_symbol, expiry),
            "option_quote": self.get_option_quote(option_ticker),
            "option_last_trade": self.get_option_last_trade(option_ticker),
        }

# class PolygonDataFetcher:
#     """Fetches live data from Polygon.io for market odds calculation."""

#     def __init__(self, api_key: Optional[str] = None, client: Optional[RESTClient] = None):
#         if client:
#             self.client = client
#         else:
#             api_key = api_key or os.getenv("POLYGON_API_KEY")
#             if not api_key:
#                 raise ValueError("A Polygon API key must be provided.")
#             self.client = RESTClient(api_key)

#     def get_last_stock_price(self, stock_symbol: str) -> Optional[Decimal]:
#         """
#         Fetch the last trade price for a given stock symbol.
#         """
#         try:
#             resp = self.client.get_last_trade(stock_symbol)
#             # The SDK may return an object or dict; handle both
#             price = getattr(resp, "price", None) if not isinstance(resp, dict) else resp.get("price")
#             if price is not None:
#                 return Decimal(str(price))
#             logger.warning(f"No last trade price found for stock {stock_symbol}.")
#         except Exception as e:
#             logger.error(f"Error fetching last stock price for {stock_symbol}: {e}")
#         return None

#     def get_historical_stock_close(self, stock_symbol: str, query_date: date) -> Optional[Decimal]:
#         """
#         Fetch the closing price of a stock on a specific date (using daily open/close endpoint).
#         """
#         try:
#             resp = self.client.get_daily_open_close(stock_symbol, query_date.strftime("%Y-%m-%d"))
#             close = getattr(resp, "close", None) if not isinstance(resp, dict) else resp.get("close")
#             if close is not None:
#                 return Decimal(str(close))
#             logger.warning(f"No close price for {stock_symbol} on {query_date}.")
#         except Exception as e:
#             logger.error(f"Error fetching close price for {stock_symbol} on {query_date}: {e}")
#         return None

#     def get_option_contracts(
#         self,
#         underlying_ticker: str,
#         strike_price: Optional[float] = None,
#         expiration_date: Optional[str] = None,
#         contract_type: Optional[str] = None,
#         limit: int = 1000
#     ) -> List[Dict[str, Any]]:
#         """
#         List option contracts for an underlying using /v3/reference/options/contracts.
#         Filters on strike_price and expiration_date are applied after fetching.
#         """
#         try:
#             contracts = []
#             iterator = self.client.list_options_contracts(
#                 underlying_ticker=underlying_ticker,
#                 contract_type=contract_type,
#             )
#             for i, contract in enumerate(iterator):
#                 if limit and i >= limit:
#                     break
#                 if strike_price is not None and getattr(contract, "strike_price", None) != strike_price:
#                     continue
#                 if expiration_date is not None and getattr(contract, "expiration_date", None) != expiration_date:
#                     continue
#                 # Convert to dict for easy downstream use
#                 contracts.append(contract.__dict__ if hasattr(contract, "__dict__") else contract)
#             return contracts
#         except Exception as e:
#             logger.error(f"Error fetching option contracts for {underlying_ticker}: {e}")
#             return []

#     def get_option_quote(self, option_ticker: str) -> Optional[Dict[str, Any]]:
#         """
#         Fetch the latest NBBO quote for a given option ticker.
#         """
#         try:
#             resp = self.client.get_option_last_quote(option_ticker)
#             # The SDK may return an object or dict; handle both
#             return resp.get("results") if isinstance(resp, dict) else getattr(resp, "results", None)
#         except Exception as e:
#             logger.error(f"Error fetching option quote for {option_ticker}: {e}")
#             return None

#     def get_option_last_trade(self, option_ticker: str) -> Optional[Dict[str, Any]]:
#         """
#         Fetch the last trade for a given option ticker.
#         """
#         try:
#             resp = self.client.get_option_last_trade(option_ticker)
#             return resp.get("results") if isinstance(resp, dict) else getattr(resp, "results", None)
#         except Exception as e:
#             logger.error(f"Error fetching option last trade for {option_ticker}: {e}")
#             return None

#     def get_options_snapshot(self, underlying_ticker: str, option_ticker: str) -> Optional[Dict[str, Any]]:
#         """
#         Fetch an options chain snapshot for a given underlying and option contract.
#         """
#         try:
#             resp = self.client.get_snapshot_option(underlying_ticker, option_ticker)
#             return resp.get("results") if isinstance(resp, dict) else getattr(resp, "results", None)
#         except Exception as e:
#             logger.error(f"Error fetching options snapshot for {underlying_ticker} / {option_ticker}: {e}")
#             return None

#     def get_market_status(self) -> Optional[Dict[str, Any]]:
#         """
#         Fetch the current market status.
#         """
#         try:
#             resp = self.client.get_market_status()
#             return resp
#         except Exception as e:
#             logger.error(f"Error fetching market status: {e}")
#             return None

#     # Utility method for fetching all data needed to update a market's odds
#     def fetch_data_for_market_odds(
#         self, stock_symbol: str, option_ticker: str, expiry: date
#     ) -> Dict[str, Any]:
#         """
#         Aggregate all relevant data for updating market odds in one call.
#         """
#         return {
#             "last_stock_price": self.get_last_stock_price(stock_symbol),
#             "historical_close": self.get_historical_stock_close(stock_symbol, expiry),
#             "option_quote": self.get_option_quote(option_ticker),
#             "option_last_trade": self.get_option_last_trade(option_ticker),
#         }