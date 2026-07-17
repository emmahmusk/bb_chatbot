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

Example:

```json
{
  "message": "If I invest $300 in Apple today, what could it be worth in 6 months?",
  "history": [],
  "top_k": 10
}
```

The response includes `answer`, the model/as-of time, and the exact market rows used
under `sources`. The chat endpoint automatically builds the index if it is empty.
For fresher data, schedule `python manage.py sync_markets --prune` (for example with a
Render cron job) at the cadence used by the main market feed.

## Render

Create a Blueprint from the repository's root `render.yaml`, set the secret values,
and attach a persistent disk if you want the SQLite embedding cache to survive deploys.
For larger datasets or multiple web instances, switch `MarketDocument` to Postgres
with pgvector; the retrieval interface is intentionally isolated for that migration.

Important: the source endpoint paginates and only returns active future markets. The
service therefore answers from available BullBear markets, not live exchange prices,
and must not present implied probabilities as guaranteed investment returns.
