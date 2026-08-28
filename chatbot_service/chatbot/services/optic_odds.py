import logging
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.core.cache import cache
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class OpticOddsError(RuntimeError):
    pass


PREVIEW_BOOKS = [
    {"id": "draftkings", "name": "DraftKings", "logo": "", "is_active": True},
    {"id": "betmgm", "name": "BetMGM", "logo": "", "is_active": True},
    {"id": "fanduel", "name": "FanDuel", "logo": "", "is_active": True},
    {"id": "caesars", "name": "Caesars", "logo": "", "is_active": True},
    {"id": "bet365", "name": "bet365", "logo": "", "is_active": True},
    {"id": "fanatics", "name": "Fanatics Sportsbook", "logo": "", "is_active": True},
]

PREVIEW_SPORTS = [
    {"id": "basketball", "name": "Basketball", "main_markets": [{"id": "moneyline", "name": "Moneyline"}, {"id": "point_spread", "name": "Point Spread"}, {"id": "total_points", "name": "Total Points"}]},
    {"id": "football", "name": "Football", "main_markets": [{"id": "moneyline", "name": "Moneyline"}, {"id": "point_spread", "name": "Point Spread"}, {"id": "total_points", "name": "Total Points"}]},
    {"id": "soccer", "name": "Soccer", "main_markets": [{"id": "moneyline", "name": "Moneyline"}, {"id": "total_goals", "name": "Total Goals"}]},
    {"id": "baseball", "name": "Baseball", "main_markets": [{"id": "moneyline", "name": "Moneyline"}, {"id": "run_line", "name": "Run Line"}, {"id": "total_runs", "name": "Total Runs"}]},
    {"id": "hockey", "name": "Hockey", "main_markets": [{"id": "moneyline", "name": "Moneyline"}, {"id": "puck_line", "name": "Puck Line"}, {"id": "total_goals", "name": "Total Goals"}]},
    {"id": "tennis", "name": "Tennis", "main_markets": [{"id": "moneyline", "name": "Moneyline"}]},
]
PREVIEW_LEAGUES = {
    "basketball": [{"id": "nba", "name": "NBA"}, {"id": "ncaab", "name": "NCAAB"}, {"id": "wnba", "name": "WNBA"}],
    "football": [{"id": "nfl", "name": "NFL"}, {"id": "ncaaf", "name": "NCAAF"}],
    "soccer": [{"id": "england_-_premier_league", "name": "England - Premier League"}, {"id": "uefa_-_champions_league", "name": "UEFA - Champions League"}],
    "baseball": [{"id": "mlb", "name": "MLB"}],
    "hockey": [{"id": "nhl", "name": "NHL"}],
    "tennis": [{"id": "atp", "name": "ATP"}, {"id": "wta", "name": "WTA"}],
}
PREVIEW_FIXTURES = [{"id": "preview-basketball-001", "label": "Celtics @ Lakers · Preview game", "start_date": None}]


def _base_url():
    return getattr(settings, "OPTIC_ODDS_BASE_URL", "https://api.opticodds.com/api/v3").rstrip("/")


def _headers():
    api_key = getattr(settings, "OPTIC_ODDS_API_KEY", "")
    return {"X-Api-Key": api_key, "Accept": "application/json"} if api_key else {"Accept": "application/json"}


def _request(path, params=None):
    if not getattr(settings, "OPTIC_ODDS_API_KEY", ""):
        return None
    try:
        response = requests.get(
            f"{_base_url()}/{path.lstrip('/')}",
            params=params or {},
            headers=_headers(),
            timeout=getattr(settings, "OPTIC_ODDS_TIMEOUT_SECONDS", 12),
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("data", payload)
    except (requests.RequestException, ValueError) as exc:
        logger.exception("OpticOdds request failed: %s", path)
        raise OpticOddsError("OpticOdds is temporarily unavailable.") from exc


def sportsbooks():
    data = _request("sportsbooks")
    if data is None:
        return PREVIEW_BOOKS, True
    if isinstance(data, dict):
        data = data.get("sportsbooks") or data.get("books") or []
    books = [book for book in data if book.get("is_active", True)]
    return books, False


def _list_data(data, *keys):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def catalog(*, sport=None, league=None, bootstrap=False):
    """Return provider-backed sports, active leagues, and supported markets."""
    if not getattr(settings, "OPTIC_ODDS_API_KEY", ""):
        sports = PREVIEW_SPORTS
        leagues = PREVIEW_LEAGUES.get((sport or "basketball").casefold(), [])
        selected_sport = next((item for item in sports if item["id"] == (sport or "basketball")), sports[0])
        markets = selected_sport.get("main_markets", [])
        return {"sports": sports, "leagues": leagues, "markets": markets, "fixtures": PREVIEW_FIXTURES}, True

    if bootstrap:
        return {"sports": _list_data(_request("sports"), "sports"), "leagues": [], "markets": [], "fixtures": []}, False

    cache_key = f"opticodds-catalog:{sport or 'all'}:{league or 'all'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached, False

    league_params = {"sport": sport} if sport else {}
    market_params = {"markets_only": "true"}
    if sport:
        market_params["sport"] = sport
    if league:
        market_params["league"] = league
    fixture_params = None
    if league:
        fixture_params = {
            "sport": sport,
            "league": league,
            "start_date_after": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    # These resources are independent; parallel requests remove three network
    # round trips from the dropdown's critical path.
    with ThreadPoolExecutor(max_workers=4 if fixture_params else 3) as executor:
        sports_future = executor.submit(_request, "sports")
        leagues_future = executor.submit(_request, "leagues/active", league_params)
        markets_future = executor.submit(_request, "markets", market_params)
        sports = _list_data(sports_future.result(), "sports")
        leagues = _list_data(leagues_future.result(), "leagues")
        raw_markets = _list_data(markets_future.result(), "markets")
        raw_fixtures = []
        if fixture_params:
            fixtures_future = executor.submit(_request, "fixtures", fixture_params)
            raw_fixtures = _list_data(fixtures_future.result(), "fixtures")
    markets = []
    for item in raw_markets:
        if item.get("id"):
            markets.append({"id": item["id"], "name": item.get("name") or item["id"]})
    fixtures = []
    for fixture in raw_fixtures:
        fixture_id = fixture.get("id") or fixture.get("fixture_id")
        if not fixture_id:
            continue
        home = fixture.get("home_team_display") or (fixture.get("home_competitors") or [{}])[0].get("name", "Home")
        away = fixture.get("away_team_display") or (fixture.get("away_competitors") or [{}])[0].get("name", "Away")
        fixtures.append({
            "id": fixture_id,
            "label": f"{away} @ {home}",
            "start_date": fixture.get("start_date"),
            "status": fixture.get("status"),
            "has_odds": fixture.get("has_odds", True),
        })
    result = {"sports": sports, "leagues": leagues, "markets": markets, "fixtures": fixtures}
    cache.set(cache_key, result, getattr(settings, "OPTIC_ODDS_CATALOG_CACHE_SECONDS", 60))
    return result, False


def _american_to_decimal(price):
    try:
        price = float(price)
        return round(1 + price / 100, 2) if price > 0 else round(1 + 100 / abs(price), 2)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _normalise_snapshot(items, selected_books):
    if isinstance(items, dict):
        items = items.get("fixtures") or items.get("odds") or []
    rows = []
    for fixture in items or []:
        fixture_id = fixture.get("id") or fixture.get("fixture_id")
        home = (fixture.get("home_competitors") or [{}])[0].get("name", "Home")
        away = (fixture.get("away_competitors") or [{}])[0].get("name", "Away")
        for odd in fixture.get("odds", []):
            book = odd.get("sportsbook") or odd.get("bookmaker") or "Unknown"
            if isinstance(book, dict):
                book = book.get("name") or book.get("id") or "Unknown"
            price = odd.get("price")
            rows.append({
                "fixture_id": fixture_id,
                "event": f"{away} @ {home}",
                "start_date": fixture.get("start_date"),
                "status": fixture.get("status", "unplayed"),
                "sportsbook": book,
                "market": odd.get("market") or odd.get("market_id") or "Moneyline",
                "selection": odd.get("selection") or odd.get("name") or "Selection",
                "points": odd.get("points"),
                "price": price,
                "decimal": _american_to_decimal(price),
                "deep_link": odd.get("deep_link"),
                "updated_at": odd.get("timestamp"),
            })
    return rows


def _preview_snapshot(selected_books):
    names = {book["id"]: book["name"] for book in PREVIEW_BOOKS}
    books = [names.get(book, book) for book in (selected_books or [book["id"] for book in PREVIEW_BOOKS[:3]])]
    selections = [("Lakers", -115), ("Celtics", 105)]
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "fixture_id": "preview-basketball-001",
            "event": "Boston Celtics @ Los Angeles Lakers",
            "start_date": now,
            "status": "unplayed",
            "sportsbook": book,
            "market": "Moneyline",
            "selection": selection,
            "points": None,
            "price": price + (index * 5 if selection == "Lakers" else -index * 5),
            "decimal": _american_to_decimal(price + (index * 5 if selection == "Lakers" else -index * 5)),
            "deep_link": None,
            "updated_at": now,
        }
        for index, book in enumerate(books)
        for selection, price in selections
    ]


def compare_odds(*, fixture_id, sport, league, market, selected_books):
    if not getattr(settings, "OPTIC_ODDS_API_KEY", ""):
        return _preview_snapshot(selected_books), True

    params = {
        "fixture_id": fixture_id,
        "odds_format": "AMERICAN",
        "is_main": "true",
        "exclude_fees": "false",
    }
    if sport:
        params["sport"] = sport
    if league:
        params["league"] = league
    if market:
        params["market"] = market
    for book in selected_books:
        params.setdefault("sportsbook", []).append(book)
    payload = _request("fixtures/odds", params)
    return _normalise_snapshot(payload, selected_books), False
