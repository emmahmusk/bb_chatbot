# Bet Settlement and Wallet Credit Endpoint Contracts

This document covers the three endpoints you requested:

- AdminSettleBetView (admin manual settlement override)
- WalletCredit functionality endpoint (bulk credit of won bets/parlays)
- BulkResolve endpoint in betengine (bulk market + bet/parlay settlement)

## Base Routing

Configured in [server/src/core/urls.py](server/src/core/urls.py):

- betengine base: `/bet/`
- admin_panel base: `/admin_panel/`

---

## 1) AdminSettleBetView

Source:

- View: [server/src/admin_panel/api.py](server/src/admin_panel/api.py)
- URL: [server/src/admin_panel/urls.py](server/src/admin_panel/urls.py)

### Endpoint

- Method: `POST`
- Path: `/admin_panel/bets/{bet_id}/settle/`
- Auth/Permission: `IsAuthenticated`

### Purpose

Manually settle a single bet by:

- forcing an outcome via `override_outcome`, or
- auto-calculating outcome using current stock price from Alpha Vantage when no override is supplied.

### Path Params

- `bet_id` (required, integer)

### Request Body

All fields optional.

- `override_outcome` (optional): `"won" | "lost" | "void"`

Examples:

```json
{}
```

```json
{
  "override_outcome": "void"
}
```

### Settlement Rules

- If market is not expired (`today < market.expiry_date`) => reject.
- If `override_outcome` is provided and valid:
  - use it directly
  - set `override_used = true`
  - skip stock price fetch
- If no override:
  - fetch final stock price via Alpha Vantage
  - determine outcome from `chosen_outcome` and target price:
    - `over`: won if final_price > target_price; void if equal
    - `under`: won if final_price < target_price; void if equal
    - otherwise lost
  - set `override_used = false`

### Payout Rules

- `won`: `payout_amount = bet.get_potential_payout()`
- `lost`: `payout_amount = 0.00`
- `void`: `payout_amount = amount_wagered`

### Success Response (200)

```json
{
  "message": "Bet 123 settled as won.",
  "override_used": true,
  "final_price": null,
  "bet": {
    "id": 123,
    "status": "won",
    "payout_amount": "15.00"
  }
}
```

### Error Responses

- `404`: bet not found
- `400`: market missing for bet
- `400`: market not yet expired
- `400`: invalid `override_outcome`
- `400`: could not fetch stock price for auto settlement

### Notes

- This endpoint settles bet status and payout amount only.
- It does **not** perform wallet credit directly.
- Wallet credit is handled by the wallet-credit endpoint below.

---

## 2) WalletCredit Functionality (CreditWinningBetsAPIView)

Source:

- View: [server/src/betengine/views.py](server/src/betengine/views.py)
- URL: [server/src/betengine/urls.py](server/src/betengine/urls.py)

### Endpoint

- Method: `POST`
- Path: `/bet/wallets/bulk-cr/`
- Auth/Permission: No explicit permission class on this view (inherits project defaults, if any)

### Purpose

Credits wallet coin balances for already-settled winnings that are not yet paid:

- Singles: won non-parlay bets where `is_paid = false`
- Parlays: won parlay bets where one or more legs still have `is_paid = false`

### Request Body

No body required.

```json
{}
```

### Credit Logic

#### Singles

For each winning single bet:

- credit `wallet.coin_balance += bet.payout_amount`
- create transaction log (`Transaction.CREDIT`)
- mark `bet.is_paid = true`

#### Parlays

For each winning parlay candidate:

- lock parlay row
- ensure all leg statuses are final and all are `won`
- if payout amount <= 0:
  - mark unpaid legs as paid without wallet credit
- else:
  - credit `wallet.coin_balance += parlay.payout_amount`
  - create transaction log (`Transaction.CREDIT`)
  - mark unpaid legs as paid

### Success Response (200)

```json
{
  "message": "success",
  "total_credited": 8,
  "singles_credited": 6,
  "parlays_credited": 2,
  "total_amount_paid": 143.5
}
```

### No-op Response (200)

```json
{
  "message": "No unpaid settled winnings found."
}
```

### Notes

- Credits are in **coin balance** (`wallet.coin_balance`).
- Transaction references are auto-generated and unique.
- Designed to be safe for repeated runs due to `is_paid` checks.

---

## 3) BulkResolve (ResolveExpiredMarketsAPIView)

Source:

- View: [server/src/betengine/views.py](server/src/betengine/views.py)
- URL: [server/src/betengine/urls.py](server/src/betengine/urls.py)

### Endpoint

- Method: `POST`
- Path: `/bet/bulk_resolve/`
- Auth/Permission: No explicit permission class on this view (inherits project defaults, if any)

### Purpose

Bulk-settles expired markets and all pending bets/parlays tied to those expired markets.

### Request Body

No body required.

```json
{}
```

### Resolution Scope

- Markets with `expiry_date <= today` and at least one pending bet.
- Uses `market.stock.last_price` as final price source.

### Market + Single Bet Logic

For each expired market:

- if stock price missing => skip market and report in `skipped_markets`
- else settle each pending single bet (`is_parlay_leg = false`):
  - `over`: won if final_price >= target_price
  - `under`: won if final_price <= target_price
  - invalid side => void
- set each bet status, payout, settled timestamp
- reset market guardrail/exposure flags:
  - `exposure_over = 0`
  - `exposure_under = 0`
  - `is_suspended_over = false`
  - `is_suspended_under = false`
  - `requires_admin_override = false`
  - `is_active = false`

### Parlay Logic

For each pending parlay:

- only process if all legs are expired
- skip if any leg market price is missing
- settle each pending leg using leg market target vs stock last_price
- determine final parlay outcome after legs:
  - any `void` leg => parlay `void`
  - all `won` => parlay `won` with potential payout
  - otherwise `lost`
- set parlay `settled_at`

### Success Response (200)

```json
{
  "message": "✅ Resolved 12 expired markets",
  "total_markets": 12,
  "resolved_bets": 98,
  "resolved_parlays": 4,
  "skipped_markets_count": 1,
  "skipped_markets": [
    {
      "market_id": 66,
      "symbol": "TSLA",
      "expiry_date": "2026-03-18",
      "reason": "missing_stock_price"
    }
  ],
  "skipped_parlays_count": 1,
  "skipped_parlays": [
    {
      "parlay_id": 77,
      "missing_symbols": ["NVDA"],
      "reason": "missing_stock_price"
    }
  ]
}
```

### No-op Response (200)

```json
{
  "message": "No expired markets found to resolve."
}
```

---

## Operational Order (Recommended)

For settlement jobs, run in this order:

1. `POST /bet/bulk_resolve/`
2. `POST /bet/wallets/bulk-cr/`

Reason:

- bulk resolve sets final outcomes and payout amounts
- wallet credit then pays only unresolved unpaid winners

---

## Security and Hardening Notes

Current implementation notes from source:

- `AdminSettleBetView` uses `IsAuthenticated` (not strict admin-only permission).
- `ResolveExpiredMarketsAPIView` has no explicit auth/permission in the view.
- `CreditWinningBetsAPIView` has no explicit auth/permission in the view.

If this is production-facing, consider adding stricter admin permission (for example `IsAdmin`/`IsAdminUser`) to bulk resolve and bulk credit endpoints.
