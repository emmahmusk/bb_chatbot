from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from chatbot.services.market_api import iter_markets


def market(market_id, symbol, expiry="Fri, 21 Aug 2026"):
    return {
        "id": market_id,
        "stock": {"symbol": symbol, "company_name": symbol},
        "expiry_date": expiry,
    }


def response(results, next_url=None):
    result = Mock()
    result.raise_for_status.return_value = None
    result.json.return_value = {"results": results, "next": next_url}
    return result


@override_settings(
    MARKET_API_BASE_URL="https://markets.example",
    MARKET_API_PATH="/bet/markets/",
    MARKET_SYNC_PAGE_SIZE=100,
    MARKET_SYNC_MAX_PAGES=5,
    MARKET_API_TIMEOUT_SECONDS=10,
)
class MarketAPITests(SimpleTestCase):
    @patch("chatbot.services.market_api.requests.get")
    def test_full_sync_discovers_symbols_then_fetches_every_symbol_page(self, get):
        def side_effect(url, params=None, timeout=None):
            if params == {"page_size": 100}:
                return response([market(1, "AAPL"), market(9, "META")])
            if params and params.get("search") == "AAPL":
                return response([market(1, "AAPL")], "https://markets.example/bet/markets/?search=AAPL&page=2")
            if "page=2" in url:
                return response([market(2, "AAPL")])
            if params and params.get("search") == "META":
                return response([market(9, "META")])
            raise AssertionError(f"Unexpected request: {url} {params}")

        get.side_effect = side_effect
        rows = list(iter_markets())

        self.assertEqual([row["id"] for row in rows], [1, 2, 9])
        self.assertEqual(get.call_count, 4)

    @patch("chatbot.services.market_api.requests.get")
    def test_explicit_symbol_skips_discovery_and_filters_exact_symbol(self, get):
        get.return_value = response([market(1, "AAPL"), market(2, "AAPLX")])

        rows = list(iter_markets(["aapl"]))

        self.assertEqual([row["id"] for row in rows], [1])
        self.assertEqual(get.call_args.kwargs["params"]["search"], "AAPL")
