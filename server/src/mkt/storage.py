# storage.py (or inside ingest.py — your choice)
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.db import transaction, DatabaseError
from typing import Dict, List
import logging
from django.conf import settings
import time
from django.utils import timezone
logger = logging.getLogger(__name__)

# Import your model
from .models import OptionData

BATCH_SIZE = getattr(settings, "OPTION_INGEST_BATCH_SIZE", 500)

def _to_decimal(value):
    if value in ("", None, "null"):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

def _to_int(value):
    if value in ("", None, "null"):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None

def _to_date(value):
    if value in ("", None, "null"):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _filter_contracts_for_market_relevance(symbol: str, contracts: List[Dict], current_price):
    """
    Keep only option contracts that can produce an eligible market under the
    current platform rules.

    Rules mirrored from market population:
    - expiration must be in the future
    - strike must be within the live price band
    - both call and put must exist for the logical key
    - both marks must be positive
    - implied probabilities must satisfy the 20%-80% guardrail
    """
    if current_price in (None, "", "null"):
        return contracts, False

    try:
        current_price = Decimal(str(current_price))
    except (InvalidOperation, ValueError, TypeError):
        return contracts, False

    if current_price <= 0:
        return contracts, False

    from betengine.models import Market
    from .utils import calculate_implied_probability_risk_neutral

    today = timezone.now().date()
    min_expiry_date = today + timedelta(days=1)
    lower_bound = current_price * Decimal("0.85")
    upper_bound = current_price * Decimal("1.15")

    grouped = {}
    for contract in contracts:
        if not isinstance(contract, dict):
            continue

        expiration = _to_date(contract.get("expiration"))
        strike = _to_decimal(contract.get("strike"))
        option_type = str(contract.get("type") or "").lower()

        if (
            not expiration
            or expiration < min_expiry_date
            or strike is None
            or option_type not in ("call", "put")
        ):
            continue

        key = (str(contract.get("symbol") or symbol).upper(), expiration, strike)
        grouped.setdefault(key, {"call": None, "put": None})
        grouped[key][option_type] = contract

    filtered_contracts = []
    for (_, expiration, strike), pair in grouped.items():
        call = pair.get("call")
        put = pair.get("put")
        if not (call and put):
            continue

        if not (lower_bound <= strike <= upper_bound):
            continue

        call_mark = _to_decimal(call.get("mark"))
        put_mark = _to_decimal(put.get("mark"))
        if call_mark is None or put_mark is None or call_mark <= 0 or put_mark <= 0:
            continue

        try:
            p_over, p_under = calculate_implied_probability_risk_neutral(
                call_mark=call_mark,
                put_mark=put_mark,
            )
        except Exception:
            continue

        if not Market.probabilities_within_guardrail(p_over, p_under):
            continue

        filtered_contracts.extend([call, put])

    return filtered_contracts, True

def populate_option_contracts_from_batch(
    all_data: Dict[str, List[Dict]],
    job_start: float = None,
    job_budget: int = 240,
    current_prices: Dict[str, Decimal] | None = None,
) -> List[str]:
    """
    Ingests and updates OptionData from a batch (symbol -> list-of-contract-dicts).
    Returns list of processed symbols.
    Uses bulk_create and bulk_update per symbol to minimize DB round-trips.
    """
    if not all_data:
        return []

    processed_symbols = set()
    total_written = 0
    today = timezone.now().date()
    min_expiry_date = today + timedelta(days=1)

    for symbol, contracts in all_data.items():
        # Check time budget
        if job_start and (time.time() - job_start) > (job_budget - 10):
            logger.warning("Time budget reached while inserting option contracts — stopping and returning partial results.")
            break

        if not isinstance(contracts, list) or not contracts:
            continue

        symbol_key = str(symbol).upper()
        relevant_contracts, used_relevance_filter = _filter_contracts_for_market_relevance(
            symbol_key,
            contracts,
            (current_prices or {}).get(symbol_key),
        )
        contracts = relevant_contracts
        if not contracts:
            if used_relevance_filter:
                OptionData.objects.filter(
                    symbol__iexact=symbol_key,
                    expiration__gte=min_expiry_date,
                ).delete()
            continue

        # Prepare filtered contracts for this symbol
        rows_to_create = []
        rows_to_update = []
        contract_ids = []
        processed_this_symbol = False

        # Precollect contractIDs for this symbol
        for c in contracts:
            if not isinstance(c, dict):
                continue
            cid = c.get("contractID")
            if cid:
                contract_ids.append(cid)

        if not contract_ids:
            continue

        # Fetch existing OptionData rows by contract_id
        existing_qs = OptionData.objects.filter(contract_id__in=contract_ids)
        existing_map = {row.contract_id: row for row in existing_qs}

        # Build create/update lists
        for c in contracts:
            if not isinstance(c, dict):
                continue
            try:
                expiration = _to_date(c.get("expiration"))
                if not expiration or expiration < min_expiry_date:
                    continue

                contract_id = c.get("contractID")
                if not contract_id:
                    continue

                fields = {
                    "contract_id": contract_id,
                    "symbol": c.get("symbol"),
                    "expiration": expiration,
                    "strike": _to_decimal(c.get("strike")),
                    "option_type": c.get("type"),
                    "mark": _to_decimal(c.get("mark")),
                    "volume": _to_int(c.get("volume")),
                    "open_interest": _to_int(c.get("open_interest")),
                    "implied_volatility": _to_decimal(c.get("implied_volatility")),
                    "delta": _to_decimal(c.get("delta")),
                    "gamma": _to_decimal(c.get("gamma")),
                    "theta": _to_decimal(c.get("theta")),
                    "vega": _to_decimal(c.get("vega")),
                    "rho": _to_decimal(c.get("rho")),
                    "quote_date": _to_date(c.get("date")),
                }

                if contract_id in existing_map:
                    # update the existing instance object
                    inst = existing_map[contract_id]
                    for k, v in fields.items():
                        setattr(inst, k, v)
                    rows_to_update.append(inst)
                else:
                    # create new instance (but don't save yet)
                    rows_to_create.append(OptionData(**fields))

                processed_this_symbol = True
            except Exception as e:
                logger.exception("Error preparing contract %s for %s: %s", c.get("contractID", "N/A"), symbol, e)
                continue

        # Write to DB in batches
        try:
            with transaction.atomic():
                # bulk_update existing rows
                if rows_to_update:
                    # determine fields to update (exclude pk)
                    update_fields = [
                        "symbol", "expiration", "strike", "option_type", "mark", "volume", "open_interest",
                        "implied_volatility", "delta", "gamma", "theta", "vega", "rho", "quote_date"
                    ]
                    # chunked bulk_update
                    for i in range(0, len(rows_to_update), BATCH_SIZE):
                        OptionData.objects.bulk_update(rows_to_update[i:i+BATCH_SIZE], update_fields, batch_size=BATCH_SIZE)
                        total_written += len(rows_to_update[i:i+BATCH_SIZE])

                # bulk_create new rows
                if rows_to_create:
                    for i in range(0, len(rows_to_create), BATCH_SIZE):
                        OptionData.objects.bulk_create(rows_to_create[i:i+BATCH_SIZE], batch_size=BATCH_SIZE)
                        total_written += len(rows_to_create[i:i+BATCH_SIZE])

                if used_relevance_filter:
                    OptionData.objects.filter(
                        symbol__iexact=symbol_key,
                        expiration__gte=min_expiry_date,
                    ).exclude(contract_id__in=contract_ids).delete()
        except DatabaseError as e:
            logger.exception("Database error while writing contracts for %s: %s", symbol, e)
            # don't mark symbol as processed if DB write failed
            continue

        if processed_this_symbol:
            processed_symbols.add(symbol)

    logger.info("Option ingestion finished. Total rows written/updated: %d", total_written)
    return list(processed_symbols)
