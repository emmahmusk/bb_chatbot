from datetime import datetime
import time
from decimal import Decimal, ROUND_HALF_UP
import traceback
from typing import Any, Dict, List, Optional
from django.conf import settings
import requests
from betengine.models import Stock
from .utils import decimal_prob_to_american

from betengine.models import Market  # adjust to your app name
from django.utils.dateparse import parse_date
from django.utils.timezone import now
from django.utils.timezone import make_aware

def sanitize_probability(prob: Decimal) -> Decimal:
    try:
        if not isinstance(prob, Decimal):
            prob = Decimal(prob)

        min_prob = Decimal("0.01")  # avoid zero for odds conversion
        max_prob = Decimal("0.99")  # cap to avoid unrealistic odds

        return max(min(prob, max_prob), min_prob)
    except Exception as e:
        print(f"[sanitize_probability ERROR] Prob: {prob}, Error: {e}")
        return Decimal("0.50")
    
def estimate_implied_probability(bid: Decimal, ask: Decimal) -> Decimal:
    try:
        bid = Decimal(bid)
        ask = Decimal(ask)

        if bid <= 0 or ask <= 0:
            raise ValueError("Bid or ask must be positive.")

        mid_price = (bid + ask) / 2
        probability = mid_price / Decimal("100.0")  # crude proxy

        return sanitize_probability(probability)
    except Exception as e:
        print(f"[estimate_implied_probability ERROR] bid={bid}, ask={ask} | {e}")
        return Decimal("0.50")  # fallback neutral probability


def apply_vig(probability: Decimal, vig: Decimal = Decimal("0.09")) -> Decimal:
    """
    Applies vig (e.g., 9%) to make the sportsbook edge realistic.
    """
    if probability <= 0 or probability >= 1:
        raise ValueError("Invalid probability for vig application.")

    overround_prob = probability + (vig * probability)
    if overround_prob >= 1:
        overround_prob = Decimal("0.99")

    return overround_prob.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def create_markets_from_options_data(stock_symbol: str, options_data: list):
    """
    Creates Market entries from option chain data for a given stock,
    computing implied probabilities and converting them to American odds.
    """
    try:
        stock = Stock.objects.get(symbol=stock_symbol)
    except Stock.DoesNotExist:
        print(f"❌ Stock not found: {stock_symbol}")
        return

    created_count = 0
    skipped_count = 0

    for option in options_data:
        try:
            strike_price = Decimal(option["strike"])
            expiration_str = option["expiration"]
            expiry_date = datetime.strptime(expiration_str, "%Y-%m-%d").date()

            bid = Decimal(option.get("bid", "0"))
            ask = Decimal(option.get("ask", "0"))

            if strike_price <= 0 or bid <= 0 or ask <= 0:
                continue

            # Skip if both already exist
            over_exists = Market.objects.filter(
                stock=stock, target_price=strike_price, expiry_date=expiry_date, outcome_type="over"
            ).exists()
            under_exists = Market.objects.filter(
                stock=stock, target_price=strike_price, expiry_date=expiry_date, outcome_type="under"
            ).exists()

            if over_exists and under_exists:
                skipped_count += 2
                continue

            # Estimate base probability and apply vig
            base_prob = estimate_implied_probability(bid, ask)
            prob_over = apply_vig(base_prob)
            prob_under = apply_vig(Decimal("1.0") - base_prob)

            # Convert to American odds (skip if invalid)
            try:
                display_odds_over = decimal_prob_to_american(prob_over)
                display_odds_under = decimal_prob_to_american(prob_under)
            except ValueError as ve:
                print(f"⚠️ Skipping strike {strike_price}: {ve}")
                continue

            if not over_exists:
                Market.objects.get_or_create(
                    stock=stock,
                    target_price=strike_price,
                    expiry_date=expiry_date,
                    outcome_type="over",
                    defaults={
                        "implied_odds_over": prob_over,
                        "implied_odds_under": Decimal("0"),
                        "display_odds_over": display_odds_over,
                        "is_active": True,
                    },
                )
                created_count += 1

            if not under_exists:
                Market.objects.get_or_create(
                    stock=stock,
                    target_price=strike_price,
                    expiry_date=expiry_date,
                    outcome_type="under",
                    defaults={
                        "implied_odds_over": Decimal("0"),
                        "implied_odds_under": prob_under,
                        "display_odds_under": display_odds_under,
                        "is_active": True,
                    },
                )
                created_count += 1

        except Exception as e:
            print(f"❌ Error creating market for {stock_symbol} strike {option.get('strike')}: {e}")

    print(f"✅ Created {created_count} new markets for {stock_symbol}, skipped {skipped_count}")

# def estimate_implied_probability(bid: Decimal, ask: Decimal) -> Decimal:
#     """
#     Estimate implied probability using midpoint of bid-ask and a simplified model.
#     """
#     try:
#         if bid > 0 and ask > 0:
#             midpoint = (bid + ask) / 2
#             # Very basic assumption: 1/midpoint gives rough implied probability if priced as 1:1 payout
#             probability = min(Decimal("1.0"), max(Decimal("0.01"), Decimal("1.0") / midpoint))
#             return round(probability, 4)
#     except Exception as e:
#         pass
#     return Decimal("0.50")  # fallback to neutral


COMPANY_MAP = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com, Inc.",
    "TSLA": "Tesla, Inc.",
    "NVDA": "NVIDIA Corporation",
    "META": "Meta Platforms, Inc.",
    "WMT": "Walmart Inc.",
    "UNH": "UnitedHealth Group Incorporated",
    "JPM": "JPMorgan Chase & Co.",
    "V": "Visa Inc.",
    "MA": "Mastercard Incorporated",
    "HD": "The Home Depot, Inc.",
    "PG": "Procter & Gamble Company",
    "XOM": "Exxon Mobil Corporation",
    "CVX": "Chevron Corporation",
    "JNJ": "Johnson & Johnson",
    "PFE": "Pfizer Inc.",
    "MRK": "Merck & Co., Inc.",
    "ABBV": "AbbVie Inc.",
    "PEP": "PepsiCo, Inc.",
    "KO": "The Coca-Cola Company",
    "DIS": "The Walt Disney Company",
    "MCD": "McDonald's Corporation",
    "NFLX": "Netflix, Inc.",
    "CSCO": "Cisco Systems, Inc.",
    "ORCL": "Oracle Corporation",
    "INTC": "Intel Corporation",
    "IBM": "International Business Machines Corporation",
    "GS": "The Goldman Sachs Group, Inc.",
    "BAC": "Bank of America Corporation",
    "C": "Citigroup Inc.",
    "T": "AT&T Inc.",
    "VZ": "Verizon Communications Inc.",
    "BA": "The Boeing Company",
    "NKE": "Nike, Inc.",
    "COST": "Costco Wholesale Corporation",
    "ADBE": "Adobe Inc.",
    "QCOM": "QUALCOMM Incorporated",
}


DOMAIN_MAP = {
    "AAPL": "apple.com",
    "MSFT": "microsoft.com",
    "GOOGL": "abc.xyz",
    "AMZN": "amazon.com",
    "TSLA": "tesla.com",
    "NVDA": "nvidia.com",
    "META": "meta.com",
    "WMT": "walmart.com",
    "UNH": "uhc.com",
    "JPM": "jpmorganchase.com",
    "V": "visa.com",
    "MA": "mastercard.com",
    "HD": "homedepot.com",
    "PG": "pg.com",
    "XOM": "exxonmobil.com",
    "CVX": "chevron.com",
    "JNJ": "jnj.com",
    "PFE": "pfizer.com",
    "MRK": "merck.com",
    "ABBV": "abbvie.com",
    "PEP": "pepsico.com",
    "KO": "coca-cola.com",
    "DIS": "disney.com",
    "MCD": "mcdonalds.com",
    "NFLX": "netflix.com",
    "CSCO": "cisco.com",
    "ORCL": "oracle.com",
    "INTC": "intel.com",
    "IBM": "ibm.com",
    "GS": "goldmansachs.com",
    "BAC": "bankofamerica.com",
    "C": "citigroup.com",
    "T": "att.com",
    "VZ": "verizon.com",
    "BA": "boeing.com",
    "NKE": "nike.com",
    "COST": "costco.com",
    "ADBE": "adobe.com",
    "QCOM": "qualcomm.com",
}

LOGO_DEV_TOKEN = getattr(settings, "LOGO_DEV_PUBLISHABLE_KEY", "YOUR_PUBLISHABLE_KEY_HERE") 

def populate_stocks():
    for symbol in COMPANY_MAP:
        name = COMPANY_MAP[symbol]
        domain = DOMAIN_MAP[symbol]
        logo_url = f"https://img.logo.dev/{domain}?token={LOGO_DEV_TOKEN}&retina=true"
        # logo_url = f"https://logo.clearbit.com/{domain}"

        try:
            stock, created = Stock.objects.update_or_create(
                symbol=symbol,
                defaults={
                    "company_name": name,
                    "url": logo_url,
                    "updated_at": now(),
                },
            )
            print(f"{'✅ Created' if created else '🔄 Updated'}: {symbol} - {name}")

        except Exception as e:
            print(f"❌ Error creating {symbol}: {e}")



def fetch_historical_options_batch(
    symbols: List[str],
    api_key: str,
    expiration_date: Optional[str] = None,
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

    for symbol in symbols:
        print(f"\nFetching: {symbol}")
        try:
            base_url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={symbol}&apikey={api_key}"
            if expiration_date:
                base_url += f"&expiration_date={expiration_date}"
            
            response = requests.get(base_url)
            response.raise_for_status()
            data = response.json()

            message = data.get("message", "")
            options = data.get("data", [])

            if not options or "error" in message.lower():
                print(f"[{symbol}] ⚠️ No data or message: {message}")
                all_data[symbol] = []
            else:
                print(f"[{symbol}] ✅ {len(options)} options fetched.")
                all_data[symbol] = options

        except requests.RequestException as e:
            print(f"[{symbol}] ❌ Request error: {e}")
            all_data[symbol] = []
        except ValueError:
            print(f"[{symbol}] ❌ Invalid JSON received.")
            all_data[symbol] = []

        time.sleep(delay_per_request)

    return all_data
