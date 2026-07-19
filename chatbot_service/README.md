# BullBear Market Chatbot Service

Standalone Django retrieval-augmented chatbot. It reads the main server's public
`/bet/markets/` endpoint, stores a local embedding index, retrieves relevant market
rows, calculates share and prediction-market scenarios, and asks OpenAI to explain
the result with the supporting market IDs.

The service root (`GET /`) provides a responsive BullBear-styled HTML/CSS/JavaScript
chat interface for testing the API without the Flutter frontend.

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
