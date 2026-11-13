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
GET /admin_panel/optic-odds/patrons/<user_id>/notes/
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
  "sportsbooks": ["draftkings", "fanduel", "pinnacle"]
}
```

The endpoint fetches a fresh snapshot, records the bet and returns a monitor
note such as `Dodgers ML | Operator X 1.91 vs. fanduel: 1.95,
pinnacle: 1.99, bet365: 1.97 | BullBear Comp Price: 1.95 | PRIME Risk Margin: +1.08% · PRIME Risk Dollar Value: $0.27`. The internal
provider slug remains configurable through `OPTIC_ODDS_PRIMARY_SPORTSBOOK`,
while `OPTIC_ODDS_PRIMARY_SPORTSBOOK_LABEL` controls this display label. It also sets
`is_potentially_bad` when the Operator X price is higher than every selected
peer, or is at least 0.20 decimal points and 10% above the lowest peer. The
thresholds are configurable with `OPTIC_ODDS_AUDIT_MIN_DECIMAL_GAP` and
`OPTIC_ODDS_AUDIT_MIN_RELATIVE_GAP`. Comparison providers are equally weighted.
The aggregate formula is `average(1/peer_decimal)`. For parlays, each provider's
leg prices are multiplied first, then `average(1/provider_combined_decimal)` is
used. Providers without a valid quote for the market or every parlay leg are
excluded from the calculation. Demo prices are used only when demo mode is
enabled or the live OpticOdds request fails; a successful live response with a
missing provider is never filled with a synthetic quote.

```text
GET /admin_panel/optic-odds/bets/monitor/?page=1&page_size=50
```

This returns the timestamped snapshots for an admin monitoring screen. These
records include `patron_id`, `patron_username`, `primary_sportsbook_label`,
`prime_risk_margin` (percentage), `prime_risk_dollar_value`, and a rule-based
`insight` object. The patron notes endpoint returns the complete slip history
plus cumulative `prime_edge_percent` and `prime_exposure`. Cumulative PRIME
Edge is calculated as `sum(evaluated wager risk dollar value) / sum(evaluated
wager stake) * 100`; PRIME Exposure is the sum of evaluated wager risk dollar
values. Parlays are counted once at slip level, so their legs are not
double-counted. These endpoints record an internal POC only; they do not place
or settle a wager with Operator X or another sportsbook.
