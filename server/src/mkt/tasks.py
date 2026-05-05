from .alpha_vantage_utils import get_current_stock_price
import logging
from typing import List
from django.db import transaction
from decimal import Decimal, InvalidOperation
from datetime import datetime
from collections import defaultdict
from django.core.cache import cache
import time

from django.conf import settings
from django.db.models import Sum
from django.db import DatabaseError

from .market_chart import ODDS_LADDER_JSON
from .models import OptionData
from betengine.models import Stock, Market, Bet
from .utils import  calculate_implied_probability_risk_neutral, get_side_and_american_odds
import requests
from django.utils import timezone
logger = logging.getLogger(__name__)

# def ingest_historical_options(symbols: list, api_key: str, date: str = None) -> list:
#     """
#     Fetch and store options data for a list of symbols from Alpha Vantage.
#     Returns a list of symbols for which data was successfully processed.
#     """
#     if not symbols:
#         print("❌ No symbols supplied.")
#         return []

#     print(f"Fetching for symbols: {symbols}")
    
#     # all_data is a dict: { "AAPL": [...], "MSFT": [...], ... }
#     all_data = fetch_historical_options_batch(symbols, api_key, date=date)

#     if not all_data:
#         print("❌ No data returned from batch fetch.")
#         return []

#     processed_symbols = []
    
#     # Filter out symbols that didn't return any data
#     valid_data = {
#         symbol: data_list 
#         for symbol, data_list in all_data.items() 
#         if data_list is not None and len(data_list) > 0
#     }

#     if not valid_data:
#         print("❌ No options returned for any symbol after filtering.")
#         return []

#     # populate_option_contracts_from_batch handles the database operations and
#     # should return a list of symbols that were successfully inserted or updated.
#     # It will also handle its own internal errors.
#     try:
#         processed_symbols = populate_option_contracts_from_batch(valid_data)
#         if processed_symbols:
#             print(f"✅ Successfully processed {len(processed_symbols)} symbols.")
#         else:
#             print("⚠️ No symbols were processed, despite having valid data.")
#     except Exception as e:
#         print(f"❌ An error occurred during database population: {e}")
#         return [] # Return an empty list on failure

#     # The function now returns the list of symbols that were successfully processed.
#     return processed_symbols

# def ingest_historical_options(symbols: list, api_key: str, date: str = None):
#     """
#     Fetch and store options data for a list of symbols from Alpha Vantage.
#     More efficient: single batch fetch, single populate call.
#     """
#     if not symbols:
#         return "No symbols supplied."

#     print(f"Fetching for symbols: {symbols}")
#     all_data = fetch_historical_options_batch(symbols, api_key, date=date)

#     # all_data is a dict: { "AAPL": [...], "MSFT": [...], ... }
#     if not all_data or all(len(v) == 0 for v in all_data.values()):
#         print("❌ No options returned for any symbol.")
#         return f"✅ Total inserted: 0 for {len(symbols)} symbols on {date or 'latest'}"

#     # Make sure populate_option_contracts_from_batch accepts the dict
#     inserted = populate_option_contracts_from_batch(all_data)
#     print(f"✅ Inserted {inserted} options across {len(symbols)} symbols.")

#     return f"✅ Total inserted: {inserted} for {len(symbols)} symbols on {date or 'latest'}"

# tasks.py (inside markets app)

def populate_market_for_stocks(stock_ids: List[int]):
    """
    Populates market data for a list of stocks.
    This function is designed to be called by an async task.
    """
    for stock_id in stock_ids:
        markets_created = 0
        try:
            stock = Stock.objects.get(id=stock_id)

            # --- Step 1: Fetch Current Stock Price ---
            try:
                current_price = stock.last_price
            except Exception as e:
                logger.exception(f"[{stock.symbol}] Price fetch failed: {e}")
                continue # Use 'continue' to move to the next stock_id

            if not current_price or current_price <= 0:
                logger.warning(f"[{stock.symbol}] Invalid price: {current_price}")
                continue # Use 'continue' to move to the next stock_id

            lower_bound = current_price * Decimal("0.85")
            upper_bound = current_price * Decimal("1.15")
            today = datetime.now().date()

            # --- Step 2: Fetch and Group Option Data ---
            try:
                option_qs = OptionData.objects.filter(
                    symbol__iexact=stock.symbol,
                    expiration__gte=today
                )
            except DatabaseError as e:
                logger.exception(f"[{stock.symbol}] DB error fetching options")
                continue # Use 'continue' to move to the next stock_id

            if not option_qs.exists():
                logger.info(f"[{stock.symbol}] No valid options data found.")
                continue # Use 'continue' to move to the next stock_id

            grouped = defaultdict(lambda: {"call": None, "put": None})
            for option in option_qs:
                try:
                    key = (option.symbol, option.expiration, Decimal(option.strike))
                    grouped[key][option.option_type] = option
                except (InvalidOperation, AttributeError):
                    logger.warning(f"[{stock.symbol}] Skipping invalid option: {option.contract_id}")
                    continue

            # --- Step 3: Calculate and Update/Create Markets ---
            for (symbol, expiration_date, strike), pair in grouped.items():
                call, put = pair.get("call"), pair.get("put")
                if not (call and put):
                    continue

                # Nested try-except block to handle calculation or DB errors for a single market
                try:
                    call_mark, put_mark = Decimal(call.mark or 0), Decimal(put.mark or 0)
                    if call_mark <= 0 or put_mark <= 0:
                        continue
                    if not (lower_bound <= strike <= upper_bound):
                        continue

                    p_over, p_under = calculate_implied_probability_risk_neutral(
                        call_mark=call_mark, put_mark=put_mark
                    )
                    if not (Decimal("0.20") <= p_over <= Decimal("0.80") and Decimal("0.20") <= p_under <= Decimal("0.80")):
                        continue

                    first_side, first_american_odd = get_side_and_american_odds(p_over, ODDS_LADDER_JSON, vig=Decimal("9.0"))
                    second_side, second_american_odd = get_side_and_american_odds(p_under, ODDS_LADDER_JSON, vig=Decimal("9.0"))

                    display_odds = {"over": first_american_odd, "under": second_american_odd}
                    ladder_favored_side = first_side.lower() if first_american_odd <= second_american_odd else second_side.lower()

                    option_volume_total = int(call.volume or 0) + int(put.volume or 0)
                    bet_volume = (
                        Bet.objects.filter(
                            market__stock=stock,
                            market__target_price=strike,
                            market__expiry_date=expiration_date,
                        ).aggregate(total=Sum("amount_wagered"))["total"] or 0
                    )
                    total_volume = option_volume_total + (2 * int(bet_volume))
                    if total_volume == 0:
                        continue

                    with transaction.atomic():
                        Market.objects.update_or_create(
                            stock=stock,
                            target_price=strike,
                            expiry_date=expiration_date,
                            outcome_type="over",
                            defaults={
                                "implied_odds_over": p_over,
                                "implied_odds_under": p_under,
                                "display_odds_over": display_odds["over"],
                                "display_odds_under": display_odds["under"],
                                "ladder_favored_side": ladder_favored_side,
                                "total_volume": total_volume,
                                "is_active": True,
                            },
                        )
                        markets_created += 1
                except Exception as e:
                    logger.exception(f"[{stock.symbol}] Market upsert failed for strike {strike}: {e}")
                    continue

            logger.info(f"[{stock.symbol}] {markets_created} markets created/updated")

        except Stock.DoesNotExist:
            logger.error(f"Stock with id={stock_id} does not exist. Skipping.")
            continue
    
    logger.info("Market population task finished for all stocks.")


def core_populate(stock, option_qs, current_price):
    """
    Core logic for building and updating markets from options.
    Keeps populate_market_for_stock cleaner.
    """
    from .market_chart import ODDS_LADDER_JSON
    from betengine.models import Market, Bet
    from .utils import (
        calculate_implied_probability_risk_neutral,
        get_side_and_american_odds,
    )

    lower_bound = current_price * Decimal("0.85")
    upper_bound = current_price * Decimal("1.15")
    today = datetime.now().date()

    grouped = defaultdict(lambda: {"call": None, "put": None})
    for option in option_qs:
        try:
            key = (option.symbol, option.expiration, Decimal(option.strike))
            grouped[key][option.option_type] = option
        except (InvalidOperation, AttributeError):
            continue

    markets_created = 0
    for (symbol, expiration_date, strike), pair in grouped.items():
        call, put = pair.get("call"), pair.get("put")
        if not (call and put):
            continue

        try:
            call_mark, put_mark = Decimal(call.mark or 0), Decimal(put.mark or 0)
        except InvalidOperation:
            continue
        if call_mark <= 0 or put_mark <= 0:
            continue
        if not (lower_bound <= strike <= upper_bound):
            continue

        try:
            p_over, p_under = calculate_implied_probability_risk_neutral(
                call_mark=call_mark, put_mark=put_mark
            )
        except ValueError:
            continue

        if not (
            Decimal("0.20") <= p_over <= Decimal("0.80")
            and Decimal("0.20") <= p_under <= Decimal("0.80")
        ):
            continue

        try:
            first_side, first_american_odd = get_side_and_american_odds(
                p_over, ODDS_LADDER_JSON, vig=Decimal("9.0")
            )
            second_side, second_american_odd = get_side_and_american_odds(
                p_under, ODDS_LADDER_JSON, vig=Decimal("9.0")
            )
        except Exception:
            continue

        display_odds = {"over": first_american_odd, "under": second_american_odd}
        ladder_favored_side = (
            first_side.lower()
            if first_american_odd <= second_american_odd
            else second_side.lower()
        )

        option_volume_total = int(call.volume or 0) + int(put.volume or 0)
        bet_volume = (
            Bet.objects.filter(
                market__stock=stock,
                market__target_price=strike,
                market__expiry_date=expiration_date,
            ).aggregate(total=Sum("amount_wagered"))["total"] or 0
        )
        total_volume = option_volume_total + (2 * int(bet_volume))
        if total_volume == 0:
            continue

        try:
            with transaction.atomic():
                Market.objects.update_or_create(
                    stock=stock,
                    target_price=strike,
                    expiry_date=expiration_date,
                    outcome_type="over",
                    defaults={
                        "implied_odds_over": p_over,
                        "implied_odds_under": p_under,
                        "display_odds_over": display_odds["over"],
                        "display_odds_under": display_odds["under"],
                        "ladder_favored_side": ladder_favored_side,
                        "total_volume": total_volume,
                        "is_active": True,
                    },
                )
                markets_created += 1
        except DatabaseError as e:
            logger.exception(f"[{stock.symbol}] Market upsert failed: {e}")
            continue

    return markets_created



# mkt/tasks.py

def ingest_and_populate(symbols, api_key, date):
    """
    Top-level background task that runs ingestion and market population.
    It acquires a distributed lock and enforces a time budget.
    """
    LOCK_KEY = "option_ingest_lock"
    LOCK_TTL = getattr(settings, "OPTION_INGEST_LOCK_TTL", 300)  # seconds
    JOB_TIME_BUDGET = getattr(settings, "OPTION_INGEST_JOB_TIME_BUDGET", 240)  # seconds

    if not cache.add(LOCK_KEY, True, LOCK_TTL):
        logger.info("Another ingest job is active — exiting immediately.")
        return

    start_time = time.time()
    try:
        normalized_symbols = [
            symbol.strip().upper()
            for symbol in symbols
            if isinstance(symbol, str) and symbol.strip()
        ]

        # Refresh stock prices even if the options ingest later returns no valid contracts.
        if normalized_symbols:
            stocks = Stock.objects.filter(symbol__in=normalized_symbols)
            for stock in stocks:
                try:
                    stock.get_current_price(api_key=api_key)
                except Exception as e:
                    logger.warning("[%s] Pre-ingest stock refresh failed: %s", stock.symbol, e)

        # Step 1: ingest live options (parallel HTTP + DB writes via bulk ops)
        from .ingest import ingest_live_options  # import local module functions
        processed_symbols = ingest_live_options(symbols, api_key, date=date, job_start=start_time, job_budget=JOB_TIME_BUDGET)

        if not processed_symbols:
            logger.info("No symbols processed; exiting.")
            return

        # Map processed symbols to stock ids
        from betengine.models import Stock
        stock_ids = list(Stock.objects.filter(symbol__in=processed_symbols).values_list("id", flat=True))
        if not stock_ids:
            logger.info("No matching stocks found for processed symbols.")
            return

        # Step 2: populate market data — function will enforce remaining time budget & re-enqueue if needed
        from .populate import populate_market_for_stocks  # import local function
        populate_market_for_stocks(stock_ids, job_start=start_time, job_budget=JOB_TIME_BUDGET)

    except Exception as e:
        logger.exception("Ingest and populate top-level task failed: %s", e)
    finally:
        # Release lock
        try:
            cache.delete(LOCK_KEY)
        except Exception:
            logger.exception("Failed to release ingest lock.")

# def ingest_and_populate(symbols, api_key, date):
#     """
#     Handles the entire workflow of ingesting data and populating the market.
#     This function will be run asynchronously by Django Q.
#     """
#     processed_symbols = ingest_historical_options(symbols, api_key, date)
    
#     if processed_symbols:
#         stock_ids = list(Stock.objects.filter(symbol__in=processed_symbols).values_list('id', flat=True))
#         populate_market_for_stocks(stock_ids)

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def ingest_from_steadyapi(symbols: List[str]):
    """
    Ingest options data from SteadyAPI for a list of symbols.
    Iterates through all weekly and monthly expirations for each symbol.
    """
    LOCK_KEY = "steadyapi_option_ingest_lock"
    try:
        BASE_URL = "https://steadyapi.com/api/v3/markets/options"
        
        processed_symbols = []
        
        if not getattr(settings, "BB_STEADY_APIKEY", None):
            logger.error("SteadyAPI: BB_STEADY_APIKEY is missing from settings!")
            return
        
        headers = {
            "Authorization": f"Bearer {settings.BB_STEADY_APIKEY}"
        }
        
        # Configure session with retries
        session = requests.Session()
        session.headers.update(headers)
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10))
        
        for ticker in symbols:
            ticker = ticker.strip().upper()
            try:
                logger.info(f"SteadyAPI: Fetching expirations for {ticker}")
                # 1. Fetch expirations
                resp = session.get(f"{BASE_URL}?ticker={ticker}", timeout=30)
                if resp.status_code != 200:
                    logger.error(f"SteadyAPI: Failed to fetch expirations for {ticker}: {resp.status_code}")
                    continue
                
                payload = resp.json()
                # Be defensive: check root, meta, and body for expirations
                expirations_data = payload.get("expirations")
                if not expirations_data:
                    expirations_data = payload.get("meta", {}).get("expirations")
                if not expirations_data:
                    expirations_data = payload.get("body", {}).get("expirations", {})
                
                weekly = expirations_data.get("weekly", [])
                monthly = expirations_data.get("monthly", [])
                all_expirations = sorted(list(set(weekly + monthly)))
                
                if not all_expirations:
                    logger.info(f"SteadyAPI: No expirations found for {ticker}. Payload keys: {list(payload.keys())}")
                    continue
                
                logger.info(f"SteadyAPI: Found {len(all_expirations)} expirations for {ticker}")
                
                for exp in all_expirations:
                    # 2. Fetch data for each expiration
                    try:
                        data_resp = session.get(f"{BASE_URL}?ticker={ticker}&expiration={exp}", timeout=30)
                        if data_resp.status_code != 200:
                            logger.warning(f"SteadyAPI: Failed to fetch data for {ticker} exp {exp}: {data_resp.status_code}")
                            continue
                        
                        payload = data_resp.json()
                    except Exception as e:
                        logger.warning(f"SteadyAPI: Connection/Parse error for {ticker} exp {exp}: {e}")
                        continue
                    
                    body = payload.get("body", {})
                    calls = body.get("Call", [])
                    puts = body.get("Put", [])
                    options_list = calls + puts
                    
                    if not options_list:
                        continue
                    
                    # Helper for cleaning numeric strings
                    def _clean_numeric(val, default=0.0):
                        if val is None or val == "N/A" or val == "unch":
                            return default
                        if isinstance(val, str):
                            # Remove commas and percentage signs
                            val = val.replace(",", "").replace("%", "")
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            return default

                    def _parse_steady_date(date_str):
                        if not date_str or date_str == "N/A":
                            return timezone.now().date()
                        try:
                            # Try full date format
                            return datetime.strptime(date_str, "%m/%d/%y").date()
                        except ValueError:
                            # If that fails, it's likely a today-timestamp like '11:24 ET'
                            # In this case, we use today's date.
                            return timezone.now().date()

                    # 3. Populate OptionData
                    for opt in options_list:
                        try:
                            strike = _clean_numeric(opt.get("strikePrice"))
                            option_type = opt.get("optionType")
                            base_symbol = opt.get("baseSymbol") or ticker
                            
                            if not strike or not option_type or not base_symbol:
                                continue

                            # SteadyAPI provided symbol looks like "AAPL|20260515|5.00C", which is a good contract_id
                            contract_id = opt.get("symbol") or f"{base_symbol}|{exp}|{strike}{option_type[0]}".upper()
                            
                            # Use the 'exp' variable directly as requested to avoid parsing errors from the body
                            expiration = datetime.strptime(exp, "%Y-%m-%d").date() if isinstance(exp, str) else exp

                            OptionData.objects.update_or_create(
                                contract_id=contract_id,
                                defaults={
                                    "symbol": base_symbol,
                                    "expiration": expiration,
                                    "strike": strike,
                                    "option_type": option_type.lower(),
                                    "mark": _clean_numeric(opt.get("midpoint")),
                                    "volume": int(_clean_numeric(opt.get("volume"))),
                                    "open_interest": int(_clean_numeric(opt.get("openInterest"))),
                                    "implied_volatility": _clean_numeric(opt.get("volatility")) / 100.0, # Convert % to decimal
                                    "delta": _clean_numeric(opt.get("delta")),
                                    "gamma": _clean_numeric(opt.get("gamma")), 
                                    "theta": _clean_numeric(opt.get("theta")),
                                    "vega": _clean_numeric(opt.get("vega")),
                                    "rho": _clean_numeric(opt.get("rho")),
                                    "quote_date": (
                                        _parse_steady_date(opt.get("tradeTime"))
                                    ),
                                }
                            )
                        except Exception as e:
                            logger.warning(f"SteadyAPI: Error parsing option data for {ticker} {exp}: {e}")
                            continue
                
                processed_symbols.append(ticker)
                logger.info(f"SteadyAPI: Successfully processed {ticker}")
                
            except Exception as e:
                logger.exception(f"SteadyAPI: Error ingesting for {ticker}: {e}")

        if processed_symbols:
            from .populate import populate_market_for_stocks
            stock_ids = list(Stock.objects.filter(symbol__in=processed_symbols).values_list("id", flat=True))
            if stock_ids:
                logger.info(f"SteadyAPI: Triggering market population for {len(stock_ids)} stocks")
                populate_market_for_stocks(stock_ids)

    finally:
        cache.delete(LOCK_KEY)

