"""Deterministic, local-only data for the Demo Odds Lab.

This module deliberately has no HTTP client and no OpticOdds dependency. It
lets operators model line movement even when the live provider or the EC2
admin proxy is unavailable.
"""
from datetime import datetime, timedelta, timezone
import re

from ..models import DemoOddsLabOverride


DEMO_SPORTS = [
    {"id": "soccer", "name": "Soccer"},
    {"id": "basketball", "name": "Basketball"},
    {"id": "baseball", "name": "Baseball"},
    {"id": "football", "name": "Football"},
    {"id": "hockey", "name": "Hockey"},
    {"id": "tennis", "name": "Tennis"},
]
DEMO_LEAGUES = {
    "soccer": [{"id": "england_-_premier_league", "name": "England - Premier League"}],
    "basketball": [{"id": "nba", "name": "NBA"}],
    "baseball": [{"id": "mlb", "name": "MLB"}],
    "football": [{"id": "nfl", "name": "NFL"}],
    "hockey": [{"id": "nhl", "name": "NHL"}],
    "tennis": [{"id": "atp", "name": "ATP"}],
}
DEMO_TEAMS = {
    "soccer": [("Arsenal FC", "Chelsea FC"), ("Liverpool FC", "Everton FC"), ("Leeds United FC", "Aston Villa FC"), ("Brighton & Hove Albion FC", "Sunderland AFC"), ("Newcastle United FC", "Tottenham Hotspur FC")],
    "basketball": [("Boston Celtics", "Los Angeles Lakers"), ("Denver Nuggets", "Phoenix Suns"), ("New York Knicks", "Milwaukee Bucks"), ("Golden State Warriors", "Dallas Mavericks"), ("Miami Heat", "Chicago Bulls")],
    "baseball": [("New York Yankees", "Boston Red Sox"), ("Los Angeles Dodgers", "San Diego Padres"), ("Atlanta Braves", "New York Mets"), ("Chicago Cubs", "St. Louis Cardinals"), ("Philadelphia Phillies", "Washington Nationals")],
    "football": [("Kansas City Chiefs", "Buffalo Bills"), ("Dallas Cowboys", "Philadelphia Eagles"), ("San Francisco 49ers", "Seattle Seahawks"), ("Baltimore Ravens", "Cincinnati Bengals"), ("Green Bay Packers", "Chicago Bears")],
    "hockey": [("Toronto Maple Leafs", "Montreal Canadiens"), ("Boston Bruins", "New York Rangers"), ("Edmonton Oilers", "Vancouver Canucks"), ("Colorado Avalanche", "Dallas Stars"), ("Florida Panthers", "Tampa Bay Lightning")],
    "tennis": [("Carlos Alcaraz", "Jannik Sinner"), ("Aryna Sabalenka", "Iga Swiatek"), ("Novak Djokovic", "Alexander Zverev"), ("Coco Gauff", "Elena Rybakina"), ("Daniil Medvedev", "Taylor Fritz")],
}
DEMO_BOOKS = ["draftkings", "fanduel", "pinnacle", "bet365"]


def _american(decimal):
    return round((decimal - 1) * 100) if decimal >= 2 else round(-100 / (decimal - 1))


def demo_fixtures(sport=None, league=None):
    sport = str(sport or "soccer").lower()
    league = league or (DEMO_LEAGUES.get(sport) or [{"id": "demo", "name": "Demo League"}])[0]["id"]
    now = datetime.now(timezone.utc).replace(microsecond=0)
    teams = DEMO_TEAMS.get(sport, DEMO_TEAMS["soccer"])
    return [
        {
            "fixture_id": f"demo-{sport}-{index + 1:03d}",
            "event": f"{away} @ {home}",
            "home_team": home,
            "away_team": away,
            "sport": sport,
            "league": league,
            "start_date": (now + timedelta(days=index + 1)).isoformat().replace("+00:00", "Z"),
            "status": "scheduled",
            "is_live": False,
            "has_odds": True,
            "demo": True,
        }
        for index, (home, away) in enumerate(teams)
    ]


def demo_odds(fixture_id, sportsbooks=None, market="moneyline"):
    fixture_id = str(fixture_id)
    match = re.search(r"demo-([a-z]+)-(\d+)", fixture_id)
    sport = match.group(1) if match else "soccer"
    index = int(match.group(2)) - 1 if match else 0
    fixtures = demo_fixtures(sport)
    fixture = fixtures[index % len(fixtures)]
    selections = ([fixture["home_team"], "Draw", fixture["away_team"]] if sport == "soccer" else [fixture["home_team"], fixture["away_team"]])
    base = [1.75, 3.60, 2.15] if sport == "soccer" else [1.78, 2.08]
    books = list(dict.fromkeys(str(book).strip().lower() for book in (sportsbooks or DEMO_BOOKS) if str(book).strip()))
    rows = []
    for book_index, book in enumerate(books):
        for selection_index, selection in enumerate(selections):
            decimal = round(base[selection_index] + book_index * 0.04 + ((index + selection_index) % 3) * 0.01, 4)
            rows.append({
                "fixture_id": fixture_id,
                "event": fixture["event"],
                "start_date": fixture["start_date"],
                "status": "scheduled",
                "sportsbook": book,
                "market": market,
                "selection": selection,
                "price": _american(decimal),
                "decimal": decimal,
                "updated_at": fixture["start_date"],
                "demo": True,
            })
    overrides = DemoOddsLabOverride.objects.filter(fixture_id=fixture_id, sportsbook__in=books, market=market, active=True)
    override_map = {(item.sportsbook.lower(), item.selection.lower()): item for item in overrides}
    for row in rows:
        item = override_map.get((row["sportsbook"].lower(), row["selection"].lower()))
        if item:
            row["decimal"] = round(float(item.decimal_odds), 4)
            row["price"] = item.american_price if item.american_price is not None else _american(row["decimal"])
            row["demo_override"] = True
    return rows


def override_payload(item):
    return {
        "id": item.id,
        "fixture_id": item.fixture_id,
        "sportsbook": item.sportsbook,
        "market": item.market,
        "selection": item.selection,
        "decimal_odds": item.decimal_odds,
        "american_price": item.american_price,
        "active": item.active,
        "updated_at": item.updated_at.isoformat(),
    }
