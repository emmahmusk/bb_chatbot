"""Small, defensive OpticOdds client used by admin sportsbook endpoints.

The provider changes the shape of nested market payloads between sports.  The
client therefore keeps the raw response available while normalising the fields
needed by the admin UI and bet monitor.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

import requests
from django.conf import settings


class OpticOddsError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "results", "fixtures", "sports", "leagues", "odds"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        if isinstance(value, dict):
            nested = _items(value)
            if nested:
                return nested
    return []


def _first(obj: dict, *keys: str, default=None):
    for key in keys:
        value = obj.get(key)
        if value not in (None, ""):
            return value
    return default


def _canonical_sportsbook(value: Any) -> str:
    """Normalize OpticOdds display names and ids to stable provider keys."""
    if isinstance(value, dict):
        value = value.get("id") or value.get("name") or value.get("key") or ""
    raw = str(value or "").strip().casefold()
    compact = re.sub(r"[^a-z0-9]", "", raw)
    aliases = {
        "hardrock": "hardrockbet",
        "hardrockbet": "hardrockbet",
        "hardrockbetsportsbook": "hardrockbet",
        "draftkings": "draftkings",
        "fanduel": "fanduel",
        "pinnacle": "pinnacle",
        "bet365": "bet365",
    }
    if compact in aliases:
        return aliases[compact]
    return re.sub(r"[^a-z0-9]+", "_", raw).strip("_")


def american_to_decimal(value: Any) -> float | None:
    try:
        american = float(value)
    except (TypeError, ValueError):
        return None
    if american > 0:
        return round(1 + american / 100, 4)
    if american < 0:
        return round(1 + 100 / abs(american), 4)
    return None


def _decimal(row: dict) -> float | None:
    value = _first(row, "decimal", "decimal_odds", "price_decimal")
    try:
        return round(float(value), 4) if value is not None else american_to_decimal(
            _first(row, "american", "american_odds", "price", "odds")
        )
    except (TypeError, ValueError):
        return None


class OpticOddsClient:
    def __init__(self):
        self.base_url = settings.OPTIC_ODDS_BASE_URL
        self.timeout = settings.OPTIC_ODDS_TIMEOUT_SECONDS
        self.session = requests.Session()
        self.session.headers.update({"X-Api-Key": settings.OPTIC_ODDS_API_KEY, "Accept": "application/json"})

    def _get(self, path: str, params: Any = None) -> Any:
        if not settings.OPTIC_ODDS_API_KEY:
            raise OpticOddsError("OPTIC_ODDS_API_KEY is not configured on the server.", 503)
        try:
            response = self.session.get(f"{self.base_url}/{path.lstrip('/')}", params=params or {}, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            detail = "OpticOdds rejected the request"
            try:
                body = response.json()
                detail = body.get("message") or body.get("error") or detail
            except Exception:
                pass
            raise OpticOddsError(detail, response.status_code) from exc
        except (requests.RequestException, ValueError) as exc:
            raise OpticOddsError("OpticOdds is temporarily unavailable.", 502) from exc

    def sports(self) -> list[dict]:
        rows = _items(self._get("sports"))
        output = []
        for x in rows:
            value = _first(x, "sport", "sport_name")
            output.append({"id": _first(x, "id", "key") or (value.get("id") if isinstance(value, dict) else value), "name": _first(x, "name") or (value.get("name") if isinstance(value, dict) else value) or _first(x, "id", "key"), "raw": x})
        return output

    def leagues(self, sport: str | None = None) -> list[dict]:
        params = {"sport": sport} if sport else {}
        rows = _items(self._get("leagues/active", params))
        output = []
        for x in rows:
            value = _first(x, "league", "league_name")
            output.append({"id": _first(x, "id", "key") or (value.get("id") if isinstance(value, dict) else value), "name": _first(x, "name") or (value.get("name") if isinstance(value, dict) else value) or _first(x, "id", "key"), "sport": _first(x, "sport", "sport_id"), "raw": x})
        return output

    def _fixture_pages(self, params: dict) -> list[dict]:
        """Read every page, rather than silently losing fixtures after page 1."""
        rows: list[dict] = []
        page = 1
        while page <= 50:
            payload = self._get("fixtures", {**params, "page": page})
            rows.extend(_items(payload))
            has_more = isinstance(payload, dict) and (payload.get("has_more") is True or str(payload.get("has_more")).lower() == "true")
            if not has_more:
                break
            page += 1
        return rows

    def fixtures(self, sport: str | None = None, league: str | None = None, live_only: bool = False, start_date_after: str | None = None, start_date_before: str | None = None) -> list[dict]:
        params = {"sport": sport, "league": league}
        if start_date_after:
            params["start_date_after"] = start_date_after
        if start_date_before:
            params["start_date_before"] = start_date_before
        rows: list[dict] = []
        if live_only:
            params["is_live"] = "true"
            rows = self._fixture_pages({k: v for k, v in params.items() if v})
        else:
            # Query both sets: a future-date filter alone can omit currently
            # live events, while is_live alone omits scheduled events.
            scheduled = self._fixture_pages({k: v for k, v in params.items() if v})
            live_params = {k: v for k, v in params.items() if v and k not in {"start_date_after", "start_date_before"}}
            live_params["is_live"] = "true"
            live = self._fixture_pages(live_params)
            rows = scheduled + live
        seen = set()
        output = []
        for x in rows:
            fixture_id = str(_first(x, "id", "fixture_id", "fixtureId", "event_id", default=""))
            if not fixture_id or fixture_id in seen:
                continue
            seen.add(fixture_id)
            status = _first(x, "status", "fixture_status", "state", default="scheduled")
            is_live = bool(_first(x, "is_live", "live", default=False)) or str(status).lower() in {"live", "in_play", "in-play"}
            home = _first(x, "home_team_display", "home_team", "home", "home_team_name")
            away = _first(x, "away_team_display", "away_team", "away", "away_team_name")
            event = _first(x, "name", "event", "fixture_name", "description") or (f"{away} @ {home}" if home and away else "")
            sport_value = _first(x, "sport", "sport_name", default=sport)
            league_value = _first(x, "league", "league_name", default=league)
            if isinstance(sport_value, dict):
                sport_value = sport_value.get("id") or sport_value.get("name")
            if isinstance(league_value, dict):
                league_value = league_value.get("id") or league_value.get("name")
            output.append({
                "fixture_id": fixture_id,
                "event": event,
                "home_team": home,
                "away_team": away,
                "sport": sport_value,
                "league": league_value,
                "start_date": _first(x, "start_date", "start_time", "commence_time"),
                "status": status,
                "is_live": is_live,
                "has_odds": _first(x, "has_odds", default=True),
                "raw": x,
            })
        return output

    def odds(self, fixture_id: str, sportsbooks: list[str], market: str | None = None) -> list[dict]:
        books = [b.strip().lower() for b in sportsbooks if b and b.strip()][:5]
        params: list[tuple[str, str]] = [("fixture_id", fixture_id), ("odds_format", "AMERICAN"), ("is_main", "true"), ("exclude_fees", "false")]
        if market:
            params.append(("market", market))
        params.extend(("sportsbook", book) for book in books)
        payload = self._get("fixtures/odds", params)
        rows: list[dict] = []

        def walk(value: Any, context: dict | None = None):
            if isinstance(value, list):
                for item in value:
                    walk(item, context)
            elif isinstance(value, dict):
                current = {**(context or {}), **value}
                provider = _canonical_sportsbook(_first(current, "sportsbook", "book", "provider", "sportsbook_name"))
                market = _first(current, "market", "market_name", "market_type", "key")
                selection = _first(current, "selection", "outcome", "participant", "name")
                price = _first(current, "price", "odds", "american", "american_odds")
                if provider and market and (selection or _first(current, "selection_line") is not None) and price is not None:
                    selection = selection or _first(current, "selection_line")
                    rows.append({
                        "fixture_id": fixture_id,
                        "event": _first(current, "event", "name", "home_team_display", default=""),
                        "start_date": _first(current, "start_date", "start_time", "commence_time"),
                        "sport": _first(current, "sport", "sport_name"),
                        "league": _first(current, "league", "league_name"),
                        "odd_id": _first(current, "id"),
                        "sportsbook": provider,
                        "market": market,
                        "selection": selection,
                        "normalized_selection": _first(current, "normalized_selection"),
                        "price": price,
                        "decimal": _decimal(current),
                        "selection_line": _first(current, "selection_line"),
                        "market_id": _first(current, "market_id"),
                        "team_id": _first(current, "team_id"),
                        "points": _first(current, "points", "line", "handicap"),
                        "deep_link": _first(current, "deep_link"),
                        "limits": _first(current, "limits"),
                        "updated_at": _first(current, "updated_at", "last_updated", "timestamp", default=datetime.now(timezone.utc).isoformat()),
                        "raw": current,
                    })
                    return
                for key, child in value.items():
                    child_context = context or {}
                    if key == "odds" and isinstance(child, list):
                        home = _first(value, "home_team_display")
                        away = _first(value, "away_team_display")
                        sport_value = _first(value, "sport", "sport_name")
                        league_value = _first(value, "league", "league_name")
                        if isinstance(sport_value, dict):
                            sport_value = sport_value.get("id") or sport_value.get("name")
                        if isinstance(league_value, dict):
                            league_value = league_value.get("id") or league_value.get("name")
                        child_context = {
                            **child_context,
                            "event": f"{away} @ {home}" if home and away else _first(value, "name", default=""),
                            "start_date": _first(value, "start_date", "start_time", "commence_time"),
                            "sport": sport_value,
                            "league": league_value,
                        }
                    if key in {"sportsbook", "book", "provider"} and isinstance(child, str):
                        child_context = {**child_context, "sportsbook": child}
                    elif key in {"market", "market_name", "market_type"} and isinstance(child, str):
                        child_context = {**child_context, "market": child}
                    walk(child, child_context)

        walk(payload)
        return rows


def default_sportsbooks() -> list[str]:
    configured = getattr(settings, "OPTIC_ODDS_COMPARISON_SPORTSBOOKS", [])
    primary = getattr(settings, "OPTIC_ODDS_PRIMARY_SPORTSBOOK", "draftkings")
    return list(dict.fromkeys([primary, *configured]))[:5]
