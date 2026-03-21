# Stock Settlement Endpoint (Admin)

## Overview
This endpoint returns **settlement-focused** data for a single stock, grouped by expiry date.
It is designed for the admin settlement details page and excludes market nudge metadata.

- Route: `GET /admin_panel/stocks/settlements/`
- Source route mapping: `server/src/admin_panel/urls.py` (`name="stock-settlement-detail"`)
- Permission: admin-only (`IsAdmin`)

---

## Query Parameters

### Required
- `symbol` (string)
  - Example: `ABBV`

### Optional filters
- `status` (string)
  - Allowed: `pending`, `won`, `lost`, `void`
- `expiry_date` (string)
  - Format: `YYYY-MM-DD`
- `target_price` (number)
  - Exact market strike/target match
- `username` (string)
  - Case-insensitive partial match
- `user_id` (integer)

---

## Example Requests

### 1) Base stock settlement view
`GET /admin_panel/stocks/settlements/?symbol=ABBV`

### 2) Filter by expiry date
`GET /admin_panel/stocks/settlements/?symbol=ABBV&expiry_date=2026-03-20`

### 3) Filter by expiry + strike + user
`GET /admin_panel/stocks/settlements/?symbol=ABBV&expiry_date=2026-03-20&target_price=210&user_id=45`

### 4) Filter by settlement status
`GET /admin_panel/stocks/settlements/?symbol=ABBV&status=won`

---

## Response Shape (200)

```json
{
  "stock": {
    "id": 12,
    "symbol": "ABBV",
    "company_name": "AbbVie Inc.",
    "last_price": "...",
    "...": "StockAdminSerializer fields"
  },
  "filters_applied": {
    "symbol": "ABBV",
    "status": "won",
    "expiry_date": "2026-03-20",
    "target_price": 210.0,
    "username": null,
    "user_id": 45
  },
  "grouped_settlements": [
    {
      "expiry_date": "Fri, 20 Mar 2026",
      "summary": {
        "total_markets": 3,
        "total_bets": 22,
        "unique_users_count": 9,
        "total_handle": 1430.0,
        "total_payout": 1195.0,
        "ggr": 235.0
      },
      "markets": [
        {
          "market_id": 987,
          "target_price": 210.0,
          "is_active": true,
          "total_bets": 8,
          "unique_users_count": 4,
          "status_counts": {
            "pending": 1,
            "won": 3,
            "lost": 4,
            "void": 0
          },
          "total_handle": 620.0,
          "total_payout": 510.0,
          "ggr": 110.0,
          "user_settlement_summary": [
            {
              "user_id": 45,
              "username": "john_admin",
              "total_bets": 3,
              "status_counts": {
                "pending": 0,
                "won": 2,
                "lost": 1,
                "void": 0
              },
              "total_wagered": 210.0,
              "total_payout": 180.0,
              "ggr": 30.0
            }
          ],
          "settlements": [
            {
              "bet_id": 3001,
              "user_id": 45,
              "username": "john_admin",
              "chosen_outcome": "over",
              "status": "won",
              "amount_wagered": 50.0,
              "payout_amount": 95.0,
              "potential_payout": 95.0,
              "placed_at": "2026-03-08 13:10:09",
              "settled_at": "2026-03-20 16:05:12"
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Error Responses

### 400 Bad Request
- Missing symbol:
```json
{"detail":"symbol parameter is required"}
```
- Invalid status:
```json
{"detail":"status must be one of: pending, won, lost, void"}
```
- Invalid expiry format:
```json
{"detail":"expiry_date must be in YYYY-MM-DD format"}
```
- Invalid target price:
```json
{"detail":"target_price must be a valid number"}
```
- Invalid user id:
```json
{"detail":"user_id must be an integer"}
```

### 404 Not Found
```json
{"detail":"Stock 'ABBV' not found"}
```

### 401 / 403
Returned when the caller is unauthenticated or lacks admin permission.

---

## Integration Notes (Admin UI)

1. Use the stock symbol from the stock list page as `symbol`.
2. Render top-level `grouped_settlements[]` by `expiry_date`.
3. Show expiry summary cards from `summary`.
4. Inside each expiry, render `markets[]` rows by `target_price`.
5. For drill-down:
   - `user_settlement_summary` = compact per-user totals
   - `settlements` = per-bet rows (table/detail drawer)
6. Use `filters_applied` to keep UI filter chips/state in sync with backend interpretation.

---

## Sorting / Behavior
- Markets are ordered by `expiry_date`, then `target_price`.
- `user_settlement_summary` is sorted by `total_bets` descending, then `username` ascending.
- If filters produce no matches, endpoint still returns `stock` + `filters_applied` with `grouped_settlements: []`.
