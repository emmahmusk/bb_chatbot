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

def populate_option_contracts_from_batch(all_data: Dict[str, List[Dict]], job_start: float = None, job_budget: int = 240) -> List[str]:
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
    min_expiry_date = today + timedelta(days=7)

    for symbol, contracts in all_data.items():
        # Check time budget
        if job_start and (time.time() - job_start) > (job_budget - 10):
            logger.warning("Time budget reached while inserting option contracts — stopping and returning partial results.")
            break

        if not isinstance(contracts, list) or not contracts:
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
        except DatabaseError as e:
            logger.exception("Database error while writing contracts for %s: %s", symbol, e)
            # don't mark symbol as processed if DB write failed
            continue

        if processed_this_symbol:
            processed_symbols.add(symbol)

    logger.info("Option ingestion finished. Total rows written/updated: %d", total_written)
    return list(processed_symbols)
