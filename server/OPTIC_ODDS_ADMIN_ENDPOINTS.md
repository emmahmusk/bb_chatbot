# Admin OpticOdds sportsbook POC

The server exposes an admin-only OpticOdds wrapper under `/admin_panel/optic-odds/`.
Every request requires the normal BullBear JWT and an admin/staff account, or
the private `X-Admin-API-Key` service header. The
OpticOdds key is read only from `OPTIC_ODDS_API_KEY` on the server.

For the chatbot Render proxy, configure the same random value as
`ADMIN_SERVER_API_KEY` on both services. This avoids expiring JWT copy/paste
while keeping the endpoints closed to the public.

Production SSM parameters used by `server/scripts/entrypoint.sh`:

```text
/bullbear/production/optic_odds/api_key
/bullbear/production/optic_odds/base_url
/bullbear/production/admin_server/api_key
```

Only the API key and admin service key are secrets. The base URL may be stored
in SSM for consistency, and defaults to `https://api.opticodds.com/api/v3` when
the SSM value is absent.

## Catalog and live/upcoming feed

```text
GET /admin_panel/optic-odds/sports/
GET /admin_panel/optic-odds/leagues/?sport=baseball
GET /admin_panel/optic-odds/fixtures/?sport=baseball&league=mlb
GET /admin_panel/optic-odds/fixtures/?sport=baseball&live_only=true
GET /admin_panel/optic-odds/fixtures/<fixture_id>/odds/?sportsbooks=draftkings,fanduel,pinnacle&market=moneyline
```

Pass at least `sport` or `league`. The fixture endpoint merges OpticOdds' live feed with scheduled fixtures and
defaults to `start_date_after=<now>`, so it does not return stale events while
still retaining live events. The odds response contains the fixture/market IDs,
selection, American and decimal price, points, limits, timestamp, and any
OpticOdds deep link supplied for a sportsbook.

## Record a simulated sportsbook bet

```http
POST /admin_panel/optic-odds/bets/
Content-Type: application/json

{
  "fixture_id": "BCE4E01B8D3D",
  "event": "Los Angeles Dodgers @ New York Mets",
  "sport": "baseball",
  "league": "mlb",
  "market": "Moneyline",
  "selection": "Los Angeles Dodgers",
  "sportsbook": "draftkings",
  "stake": "25.00",
  "sportsbooks": ["draftkings", "fanduel", "pinnacle"],
  "provider_weights": {"draftkings": 0.3333, "fanduel": 0.3333, "pinnacle": 0.3334}
}
```

The endpoint fetches a fresh snapshot, records the bet and returns a monitor
note such as `Dodgers ML | 1.91 vs. draftkings: 1.87, fanduel: 1.95,
pinnacle: 1.99 | Weighted implied probability: 52.11%`. It also sets
`is_potentially_bad` when the DraftKings price is higher than every selected
peer, or is at least 0.20 decimal points and 10% above the lowest peer. The
thresholds are configurable with `OPTIC_ODDS_AUDIT_MIN_DECIMAL_GAP` and
`OPTIC_ODDS_AUDIT_MIN_RELATIVE_GAP`. The weighted formula
is the requested comparison proxy: `sum(weight × 1/decimal)`, not a guarantee
of profit or a sportsbook's official expected-value calculation.

```text
GET /admin_panel/optic-odds/bets/monitor/?limit=50
```

This returns the timestamped snapshots for an admin monitoring screen. These
endpoints record an internal POC only; they do not place or settle a wager with
DraftKings or another sportsbook.
