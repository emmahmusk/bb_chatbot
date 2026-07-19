from urllib.parse import urljoin

import requests
from django.conf import settings


class MarketAPIError(RuntimeError):
    pass


def _endpoint_url():
    return urljoin(
        settings.MARKET_API_BASE_URL + "/",
        settings.MARKET_API_PATH.lstrip("/"),
    )


def _read_page(url, params=None):
    try:
        response = requests.get(
            url,
            params=params,
            timeout=settings.MARKET_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise MarketAPIError(f"Could not read the market API: {exc}") from exc

    results = payload.get("results", payload) if isinstance(payload, dict) else payload
    if not isinstance(results, list):
        raise MarketAPIError("Market API returned an unsupported response shape.")
    next_url = payload.get("next") if isinstance(payload, dict) else None
    return results, next_url


def _iter_query(params):
    url = _endpoint_url()
    request_params = params
    for _page_number in range(1, settings.MARKET_SYNC_MAX_PAGES + 1):
        results, next_url = _read_page(url, request_params)
        yield from results
        if not next_url:
            return
        url = next_url
        request_params = None
    raise MarketAPIError(
        "Market API pagination exceeded MARKET_SYNC_MAX_PAGES; refusing to build a partial index."
    )


def _normalize_symbols(symbols):
    return sorted(
        {
            str(symbol).strip().upper()
            for symbol in (symbols or [])
            if str(symbol).strip()
        }
    )


def _discover_active_symbols():
    symbols = set()
    for market in _iter_query({"page_size": settings.MARKET_SYNC_PAGE_SIZE}):
        symbol = str((market.get("stock") or {}).get("symbol", "")).strip().upper()
        if symbol:
            symbols.add(symbol)
    return sorted(symbols)


def iter_markets(symbols=None):
    """Yield every active market by querying the public endpoint once per symbol.

    The server's unfiltered endpoint intentionally returns one representative market
    per stock. It is used only to discover symbols; `search=SYMBOL` removes that
    distinct-per-stock behavior and exposes every paginated market for the symbol.
    """
    target_symbols = _normalize_symbols(symbols) or _discover_active_symbols()
    yielded_ids = set()

    for requested_symbol in target_symbols:
        params = {
            "page_size": settings.MARKET_SYNC_PAGE_SIZE,
            "search": requested_symbol,
        }
        for market in _iter_query(params):
            actual_symbol = str((market.get("stock") or {}).get("symbol", "")).strip().upper()
            source_id = str(market.get("id", "")).strip()
            if actual_symbol != requested_symbol or not source_id or source_id in yielded_ids:
                continue
            yielded_ids.add(source_id)
            yield market
