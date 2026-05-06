# ingest.py
import requests
import concurrent.futures
import logging
from django.conf import settings
import time
from typing import List, Dict, Any, Optional
from .storage import populate_option_contracts_from_batch  # see next section
logger = logging.getLogger(__name__)

REALTIME_OPTIONS_FMV = "https://www.alphavantage.co/query?function=REALTIME_OPTIONS_FMV"

def _fetch_single_symbol(symbol: str, api_key: str, date: Optional[str], timeout: int = 10) -> (str, List[Dict[str, Any]]):
    """Fetch one symbol and return (symbol, list_of_options) — catches all exceptions."""
    url = f"{REALTIME_OPTIONS_FMV}&symbol={symbol}&require_greeks=true&apikey={api_key}"
    if date:
        url += f"&date={date}"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        message = data.get("message", "")
        options = data.get("data", [])
        if message == "success" and isinstance(options, list):
            return symbol, options
        else:
            logger.warning("[%s] No data or message: %s", symbol, message)
            return symbol, []
    except requests.RequestException as e:
        logger.warning("[%s] Request error: %s", symbol, e)
        return symbol, []
    except ValueError:
        logger.warning("[%s] Invalid JSON returned.", symbol)
        return symbol, []

def fetch_live_options_batch_concurrent(
    symbols: List[str],
    api_key: str,
    date: Optional[str] = None,
    max_workers: int = 6,
    per_request_timeout: int = 10
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Concurrently fetch options for symbols. Returns dict symbol->options_list.
    - max_workers: concurrency; tune to your rate limit and CPU.
    - per_request_timeout: HTTP request timeout in seconds.
    """
    all_data = {}
    if not symbols:
        return all_data

    max_workers = max(1, min(max_workers, len(symbols)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_single_symbol, symbol, api_key, date, per_request_timeout): symbol
            for symbol in symbols
        }
        for fut in concurrent.futures.as_completed(futures):
            try:
                symbol, options = fut.result()
                all_data[symbol] = options or []
            except Exception as e:
                symbol = futures.get(fut, "unknown")
                logger.exception("Fetching failed for %s: %s", symbol, e)
                all_data[symbol] = []

    return all_data

# ingest.py (continued)

def ingest_live_options(
    symbols: List[str],
    api_key: str,
    date: Optional[str] = None,
    job_start: float = None,
    job_budget: int = 240,
    current_prices: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Fetch and store options for a list of symbols. Returns list of successfully processed symbols.
    This orchestrates fetch -> bulk DB writes.
    """
    if not symbols:
        logger.info("No symbols supplied to ingest_live_options.")
        return []

    logger.info("Starting fetch for %d symbols", len(symbols))
    # Tune concurrency to avoid hitting rate limits
    max_workers = getattr(settings, "OPTION_INGEST_MAX_WORKERS", 6)

    all_data = fetch_live_options_batch_concurrent(symbols, api_key, date=date, max_workers=max_workers)
    if not all_data:
        logger.warning("Empty fetch results for provided symbols.")
        return []

    # Filter out empty results early
    valid_data = {s: opts for s, opts in all_data.items() if opts and isinstance(opts, list)}

    if not valid_data:
        logger.warning("No valid options returned after filtering.")
        return []

    # Bulk persist the OptionData rows (optimized implementation)
    processed_symbols = populate_option_contracts_from_batch(
        valid_data,
        job_start=job_start,
        job_budget=job_budget,
        current_prices=current_prices,
    )
    return processed_symbols
