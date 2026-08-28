import logging
from datetime import datetime, timezone

import requests
from django.conf import settings

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
