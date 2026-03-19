# Stock Settlement Endpoint Contract

This document describes the admin stock settlements endpoint used by the admin frontend.

## Endpoint

- Method: `GET`
- Path: `/admin_panel/stocks/settlements/`
- Auth: Admin-only (same admin auth used by other admin_panel endpoints)

## Purpose

Returns settlement-focused market data for a single stock grouped by expiry date, including:

- `grouped_settlements` for current filter context
- `grouped_settlements_by_bucket.settled` (won/lost/void)
- `grouped_settlements_by_bucket.unsettled` (pending)
- boolean flags to quickly hide empty sections without extra client processing

## Query Parameters

- `symbol` (required): stock symbol, e.g. `AAPL`
- `status` (optional): one of
  - `pending`
  - `won`
  - `lost`
  - `void`
  - `settled` (maps to `won|lost|void`)
  - `unsettled` (maps to `pending`)
- `expiry_date` (optional): `YYYY-MM-DD`
- `target_price` (optional): decimal string (e.g. `120.00`)
- `username` (optional): partial username match (case-insensitive)
- `user_id` (optional): integer user id

## Response (200)

```json
{
  "stock": {
    "id": 1,
    "symbol": "AAPL",
    "company_name": "Apple Inc",
    "url": "...",
    "market_status": true,
    "auto_odds": true,
    "last_price": 190.12,
    "last_change": -1.12,
    "last_percent_change": "-0.58%"
  },
  "filters_applied": {
    "symbol": "AAPL",
    "status": "settled",
    "expiry_date": null,
    "target_price": null,
    "username": null,
    "user_id": null
  },
  "has_grouped_settlements": true,
  "has_grouped_settlements_settled": true,
  "has_grouped_settlements_unsettled": false,
  "grouped_settlements_by_bucket": {
    "settled": [
      {
        "expiry_date": "Fri, 21 Mar 2026",
        "summary": {
          "total_markets": 2,
          "total_bets": 10,
          "unique_users_count": 7,
          "total_handle": 1000.0,
          "total_payout": 820.0,
          "ggr": 180.0
        },
        "markets": [
          {
            "market_id": 123,
            "target_price": 200.0,
            "is_active": true,
            "total_bets": 4,
            "unique_users_count": 3,
            "status_counts": {
              "pending": 0,
              "won": 2,
              "lost": 2,
              "void": 0
            },
            "total_handle": 200.0,
            "total_payout": 160.0,
            "ggr": 40.0,
            "user_settlement_summary": [
              {
                "user_id": 55,
                "username": "alice",
                "total_bets": 2,
                "status_counts": {
                  "pending": 0,
                  "won": 1,
                  "lost": 1,
                  "void": 0
                },
                "total_wagered": 80.0,
                "total_payout": 60.0,
                "ggr": 20.0
              }
            ],
            "settlements": [
              {
                "bet_id": 901,
                "user_id": 55,
                "username": "alice",
                "chosen_outcome": "over",
                "status": "won",
                "amount_wagered": 40.0,
                "payout_amount": 70.0,
                "potential_payout": 70.0,
                "placed_at": "2026-03-18 10:20:10",
                "settled_at": "2026-03-19 09:20:10"
              }
            ]
          }
        ]
      }
    ],
    "unsettled": []
  },
  "grouped_settlements": [
    {
      "expiry_date": "Fri, 21 Mar 2026",
      "summary": {
        "total_markets": 2,
        "total_bets": 10,
        "unique_users_count": 7,
        "total_handle": 1000.0,
        "total_payout": 820.0,
        "ggr": 180.0
      },
      "markets": []
    }
  ]
}
```

Notes:

- `grouped_settlements` follows the active `status` filter context:
  - `status=settled` => only settled expiry groups
  - `status=unsettled` => only unsettled expiry groups
  - `status=won/lost/void/pending` => exact-status grouping
  - no `status` => all statuses
- Empty markets are omitted.
- Empty expiry groups are omitted.

## Error Responses

- `400` if
  - `symbol` missing
  - `status` invalid
  - `expiry_date` invalid format
  - `target_price` invalid number
  - `user_id` not an integer
- `404` if stock is not found

## Frontend Integration Guidance

Use the flags first for rendering decisions:

- show top-level stock card if `has_grouped_settlements` is `true`
- show Settled tab count/state from `has_grouped_settlements_settled`
- show Unsettled tab count/state from `has_grouped_settlements_unsettled`

Recommended data source per UI section:

- Settled section: `grouped_settlements_by_bucket.settled`
- Unsettled section: `grouped_settlements_by_bucket.unsettled`
- Current filter list view: `grouped_settlements`

This avoids client-side re-grouping and keeps rendering fast and accurate.
