from urllib.parse import urljoin

import requests
from django.conf import settings


class MarketAPIError(RuntimeError):
    pass


def iter_markets(symbols=None):
    url = urljoin(settings.MARKET_API_BASE_URL + "/", settings.MARKET_API_PATH.lstrip("/"))
    base_params = {"page_size": settings.MARKET_SYNC_PAGE_SIZE}
    if symbols and len(symbols) == 1:
        base_params["search"] = symbols[0]

    for page in range(1, settings.MARKET_SYNC_MAX_PAGES + 1):
        try:
            response = requests.get(
                url,
                params={**base_params, "page": page},
                timeout=settings.MARKET_API_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise MarketAPIError(f"Could not read the market API: {exc}") from exc

        results = payload.get("results", payload) if isinstance(payload, dict) else payload
        if not isinstance(results, list):
            raise MarketAPIError("Market API returned an unsupported response shape.")
        for market in results:
            symbol = str((market.get("stock") or {}).get("symbol", "")).upper()
            if not symbols or symbol in symbols:
                yield market
        if not isinstance(payload, dict) or not payload.get("next"):
            break
