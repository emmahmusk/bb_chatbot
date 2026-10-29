# BullBear Market Chatbot Service

Standalone Django retrieval-augmented chatbot. It reads the main server's public
`/bet/markets/` endpoint, stores a local embedding index, retrieves relevant market
rows, calculates share and prediction-market scenarios, and asks OpenAI to explain
the result with the supporting market IDs.

The service root (`GET /`) provides a responsive BullBear-styled HTML/CSS/JavaScript
chat interface for testing the API without the Flutter frontend.

Both browser experiences use Django's static-file pipeline. If a local browser
still shows the unstyled HTML, run `python manage.py collectstatic --noinput`,
restart the development server, and hard-refresh the page. The service enables
WhiteNoise's finder fallback so newly added assets are also available before a
collectstatic run; Render's `entrypoint.sh` always collects them during deploy.

The odds comparison experience is available at `/odds-comparison/`. It uses the
OpticOdds v3 API through `GET /api/odds/providers/` and
`POST /api/odds/compare/`, with two to five sportsbooks per comparison. Set
`OPTIC_ODDS_API_KEY` on Render to enable live prices. Without a key, the page
stays usable in clearly labelled Preview mode with sample prices; the key is
never sent to the browser.

Clicking a comparison price opens the Audit panel and checks that selection
against the same fixture, market, and outcome at the other chosen sportsbooks.
Prices that are higher than every peer, or materially above the lowest peer,
are flagged as suspicious outliers and saved with a timestamp and the full
comparison snapshot. Audit history is available through `GET /api/odds/audits/`;
new records are created with `POST /api/odds/audits/`.
Recorded selections are available through `GET /api/odds/bets/` and are created
with `POST /api/odds/bets/`.

The comparison form loads its sport, active league, and market options from the
server-side `GET /api/odds/catalog/` endpoint. The service proxies OpticOdds'
`/sports`, `/leagues/active`, `/markets`, and `/fixtures` resources so users can
choose the exact league, fixture, and market supported for the selected sport.
Catalog responses are cached briefly and the independent OpticOdds resources are
requested in parallel, keeping dropdown changes responsive while still allowing
fresh options. Adjust `OPTIC_ODDS_CATALOG_CACHE_SECONDS` if needed.
The page performs a lightweight sports-only bootstrap on first load; league,
market, and fixture data are fetched only after the user starts choosing a sport
or league.
For a selected league, fixture discovery merges upcoming events with OpticOdds'
live (`is_live=true`) events and labels in-play games with a `LIVE` prefix.

Optional OpticOdds settings:

```text
OPTIC_ODDS_BASE_URL=https://api.opticodds.com/api/v3
OPTIC_ODDS_TIMEOUT_SECONDS=12
```

## Local setup

```bash
cd chatbot_service
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py sync_markets
python manage.py collectstatic --noinput
python manage.py runserver
```

The service reads `.env` locally. `OPENAI_API_KEY` and `MARKET_API_BASE_URL` are required.

## API

- `GET /api/health/`
- `POST /api/markets/sync/` with optional `{"symbols":["AAPL"],"prune":false}`
- `POST /api/chat/`
- `GET /api/conversations/<conversation_id>/`

Example:

```json
{
  "message": "If I invest $300 in Apple today, what could it be worth in 6 months?",
  "conversation_id": "optional-uuid-returned-by-the-previous-response",
  "top_k": 10
}
```

The response includes `answer`, the model/as-of time, and the exact market rows used
under `sources`. It also returns a `conversation_id`. Send that ID on subsequent turns
so the service can load stored history, resolve references such as "same amount" or
"what about META?", and ask a clarification question when required. The web interface
stores the active ID in local browser storage and restores its messages after reloads.

Conversations and their messages are stored in the chatbot database, separately from
the main BullBear server database. "New chat" starts a fresh browser session but does
not delete historical database records. Conversation IDs are random UUIDs; an
authenticated production integration should additionally associate conversations with
the BullBear user and enforce ownership permissions.

The chat endpoint automatically builds the market index if it is empty.
For fresher data, schedule `python manage.py sync_markets --prune` (for example with a
Render cron job) at the cadence used by the main market feed.

### Rebuild after upgrading from the one-market-per-symbol index

The server's unfiltered `/bet/markets/` response contains one representative row per
stock. This service now uses that response only to discover symbols, then requests
each symbol separately and follows every pagination link. Existing deployments must
perform one full rebuild so their persistent SQLite index gains the missing expiries:

```bash
python manage.py sync_markets --prune
```

This command can create several thousand market embeddings, so run it from the Render
Shell or a background/cron job rather than during a web request. Subsequent runs embed
only new or changed markets. To refresh one stock while testing, use:

```bash
python manage.py sync_markets --symbol AAPL --prune
```

`GET /api/health/` reports the indexed market/symbol counts, expiry range, and an
`index_complete` indicator. Questions containing "nearest expiry" are ordered by the
actual earliest indexed date; questions such as "in 6 months" use the closest expiry.

## Render

Create a Blueprint from the repository's root `render.yaml`, set the secret values,
and attach a persistent disk if you want the SQLite embedding cache to survive deploys.
For larger datasets or multiple web instances, switch `MarketDocument` to Postgres
with pgvector; the retrieval interface is intentionally isolated for that migration.

Important: the source endpoint paginates and only returns active future markets. The
service therefore answers from available BullBear markets, not live exchange prices,
and must not present implied probabilities as guaranteed investment returns.

## Admin sportsbook screens

The standalone Render service includes two separate routes backed by the EC2
server's admin OpticOdds API:

- `/sportsbook/` — browse live/upcoming fixtures, select comparison books, view
  DraftKings as the baseline, and record a simulated selection.
- `/sportsbook/monitor/` — review timestamped comparison notes and potentially
  bad-bet flags. The feed refreshes automatically every 30 seconds.

The Flutter sportsbook uses `POST /api/admin-sportsbook/betslips/` for placement.
That bridge reads the comparison books saved on the monitor settings panel,
keeps DraftKings as the only betting-screen price, and forwards the authenticated
betslip to the EC2 sportsbook API. The EC2 service then stores the betslip and
the full comparison snapshot used by this monitoring page.

Configure these Render environment variables (the JWT remains server-side and
is never placed in browser JavaScript):

```text
ADMIN_SERVER_BASE_URL=https://api.bbbprediction.com
ADMIN_SERVER_API_KEY=<same-long-random-secret-as-EC2>
ADMIN_SERVER_JWT=<long-lived admin JWT>
ADMIN_SERVER_TIMEOUT_SECONDS=15
```

For the Flutter app, set its environment config `chatbotBaseUrl` to this
service's Render URL. If it is left empty, the app falls back to the direct EC2
route and uses the EC2 environment's comparison-book list instead.

On the EC2 server, configure `OPTIC_ODDS_API_KEY` (the production entrypoint
reads `/bullbear/production/optic_odds/api_key` from SSM), then run the admin
migration. The API calls made by these pages are proxied through the chatbot
service at `/api/admin-sportsbook/` and `/api/admin-monitor/`, so neither the
OpticOdds credential nor the private admin service key is exposed to the browser.
`ADMIN_SERVER_JWT` is retained only as a fallback for deployments that have not
yet switched to the service key.

For a key outage or a fully local simulation, set `SPORTSBOOK_MODE=demo` on the
EC2 server (or create `/bullbear/production/sportsbook/mode` in SSM with value
`demo`). The bet-record endpoint then skips OpticOdds entirely and fills any
missing peer quotes from deterministic demo prices. The default `auto` mode
still tries OpticOdds first and falls back automatically when the key is absent,
expired or temporarily unavailable.
