import hashlib
from datetime import datetime

from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime

from chatbot.models import MarketDocument
from .market_api import iter_markets
from .openai_client import embed_texts


def _parse_market_date(value):
    if not value:
        return None
    parsed = parse_date(str(value))
    if parsed:
        return parsed
    for fmt in ("%a, %d %b %Y", "%d %b %Y"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    return None


def _market_content(market):
    stock = market.get("stock") or {}
    over = market.get("odds_over") or {}
    under = market.get("odds_under") or {}
    return (
        f"{stock.get('company_name') or stock.get('symbol')} ({stock.get('symbol')}) market. "
        f"Current/last stock price: {stock.get('last_price')}. Target price: {market.get('target_price')}. "
        f"Expiry: {market.get('expiry_date')}. Outcome: price over target. "
        f"Implied probability over: {market.get('implied_odds_over')}; under: {market.get('implied_odds_under')}. "
        f"Over odds: American {over.get('american')}, decimal {over.get('decimal')}, fractional {over.get('fractional')}. "
        f"Under odds: American {under.get('american')}, decimal {under.get('decimal')}, fractional {under.get('fractional')}. "
        f"Active: {market.get('is_active')}. Source market id: {market.get('id')}."
    )


def sync_market_index(symbols=None, prune=False):
    symbols = {str(symbol).strip().upper() for symbol in (symbols or []) if str(symbol).strip()}
    incoming = list(iter_markets(symbols or None))
    prepared = []
    seen_ids = set()
    for market in incoming:
        source_id = str(market.get("id", "")).strip()
        symbol = str((market.get("stock") or {}).get("symbol", "")).upper()
        if not source_id or not symbol:
            continue
        content = _market_content(market)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        seen_ids.add(source_id)
        existing = MarketDocument.objects.filter(source_id=source_id).first()
        if not existing or existing.content_hash != digest or not existing.embedding:
            prepared.append((market, content, digest, existing))

    embeddings = embed_texts([item[1] for item in prepared])
    with transaction.atomic():
        for (market, content, digest, existing), embedding in zip(prepared, embeddings):
            stock = market.get("stock") or {}
            raw_updated = market.get("updated_at") or stock.get("updated_at")
            updated_at = parse_datetime(raw_updated) if isinstance(raw_updated, str) else None
            values = {
                "symbol": str(stock.get("symbol", "")).upper(),
                "company_name": str(stock.get("company_name") or ""),
                "expiry_date": _parse_market_date(market.get("expiry_date")),
                "content": content,
                "content_hash": digest,
                "payload": market,
                "embedding": embedding,
                "source_updated_at": updated_at,
            }
            MarketDocument.objects.update_or_create(source_id=str(market["id"]), defaults=values)
        deleted = 0
        if prune:
            stale = MarketDocument.objects.exclude(source_id__in=seen_ids)
            if symbols:
                stale = stale.filter(symbol__in=symbols)
            deleted, _ = stale.delete()

    indexed_symbols = {
        str((market.get("stock") or {}).get("symbol", "")).upper()
        for market in incoming
        if (market.get("stock") or {}).get("symbol")
    }
    return {
        "fetched": len(incoming),
        "symbols": len(indexed_symbols),
        "indexed": len(prepared),
        "unchanged": len(incoming) - len(prepared),
        "deleted": deleted,
    }
