import requests
import time
from typing import List, Optional, Dict, Any
from .models import OptionData
from datetime import datetime, timedelta
from decimal import Decimal
from django.db import transaction, DatabaseError


def fetch_live_options_batch(
    symbols: List[str],
    api_key: str,
    date: Optional[str] = None,
    delay_per_request: float = 0.6  # ~100 calls/min buffer for 150/min plan
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch historical options data for multiple US stocks from Alpha Vantage.

    Args:
        symbols (List[str]): List of stock symbols.
        api_key (str): Your Alpha Vantage API key.
        expiration_date (Optional[str]): Optional expiration date (YYYY-MM-DD).
        delay_per_request (float): Delay between API calls in seconds.

    Returns:
        Dict[str, List[Dict[str, Any]]]: Symbol to options data.
    """
    all_data = {}
    
    REALTIME_OPTIONS_FMV = "https://www.alphavantage.co/query?function=REALTIME_OPTIONS_FMV"

    for symbol in symbols:
        print(f"\nFetching: {symbol}")
        try:
            base_url = f"{REALTIME_OPTIONS_FMV}&symbol={symbol}&require_greeks=true&apikey={api_key}"
            if date:
                base_url += f"&date={date}"

            response = requests.get(base_url)
            response.raise_for_status()
            data = response.json()

            message = data.get("message", "")
            options = data.get("data", [])

            if message == "success":
                print(f"[{symbol}] ✅ {len(options)} options fetched.")
                all_data[symbol] = options
            else:
                print(f"[{symbol}] ⚠️ No data or message: {message}")
                all_data[symbol] = []

        except requests.RequestException as e:
            print(f"[{symbol}] ❌ Request error: {e}")
            all_data[symbol] = []
        except ValueError:
            print(f"[{symbol}] ❌ Invalid JSON received.")
            all_data[symbol] = []

        time.sleep(delay_per_request)

    return all_data



def float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def safe_parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None

def populate_option_contracts_from_batch(all_data: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """
    Ingests and updates OptionData from a batch of symbols.
    Returns a list of symbols for which at least one contract was processed.
    """


    processed_symbols = set()
    total_inserted = 0
    today = datetime.now().date()
    min_expiry_date = today + timedelta(days=7)

    def to_decimal(value: str) -> Optional[Decimal]:
        if value in ("", "null", None):
            return None
        try:
            return Decimal(value)
        except (ValueError, TypeError):
            return None

    def to_int(value: str) -> Optional[int]:
        if value in ("", "null", None):
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def to_date(value: str) -> Optional[datetime.date]:
        if value in ("", "null", None):
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    for symbol, options in all_data.items():
        symbol_processed = False
        if not isinstance(options, list):
            print(f"⚠️ Skipping invalid data for {symbol}: expected list, got {type(options)}")
            continue
        
        # Wrap the per-symbol processing in a transaction for atomicity.
        try:
            with transaction.atomic():
                for contract in options:
                    if not isinstance(contract, dict):
                        print(f"⚠️ Skipping invalid contract data for {symbol}: {contract}")
                        continue

                    try:
                        expiration = to_date(contract.get("expiration"))
                        if not expiration or expiration < min_expiry_date:
                            continue
                        OptionData.objects.update_or_create(
                            contract_id=contract.get("contractID"),
                            defaults={
                                "symbol": contract.get("symbol"),
                                "expiration": expiration,
                                "strike": to_decimal(contract.get("strike")),
                                "option_type": contract.get("type"),
                                "mark": to_decimal(contract.get("mark")),
                                "volume": to_int(contract.get("volume")),
                                "open_interest": to_int(contract.get("open_interest")),
                                "implied_volatility": to_decimal(contract.get("implied_volatility")),
                                "delta": to_decimal(contract.get("delta")),
                                "gamma": to_decimal(contract.get("gamma")),
                                "theta": to_decimal(contract.get("theta")),
                                "vega": to_decimal(contract.get("vega")),
                                "rho": to_decimal(contract.get("rho")),
                                "quote_date": to_date(contract.get("date")),
                            },
                        )
                        total_inserted += 1
                        symbol_processed = True
                    except (DatabaseError, Exception) as e:
                        # Log error and continue to the next contract within the same symbol.
                        print(f"❌ Error processing contract {contract.get('contractID', 'N/A')} for {symbol}: {e}")
                        continue  # Keep trying other contracts for this symbol
        except DatabaseError as e:
            # An atomic block failed for this symbol, log and move on to the next.
            print(f"❌ Database transaction failed for symbol {symbol}: {e}")
            continue

        if symbol_processed:
            processed_symbols.add(symbol)

    print(f"✅ Done. Total contracts inserted or updated: {total_inserted}")
    return list(processed_symbols)
def get_current_stock_price(symbol: str, api_key: str) -> Decimal:
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": api_key
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        price_str = data.get("Global Quote", {}).get("05. price")
        if price_str:
            return Decimal(price_str)
        else:
            raise ValueError("Price not found in response")
    except Exception as e:
        print(f"Error fetching stock price: {e}")
        return Decimal("0")
