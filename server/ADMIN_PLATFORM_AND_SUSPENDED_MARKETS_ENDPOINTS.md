# Admin Platform Settings and Suspended Markets API Contract

This document defines the updated contracts for:

- Platform settings endpoint
- Suspended markets list endpoint
- Suspended market detail/update endpoint

It is intended for external admin frontend integration.

## Base Route

From project routing, admin panel APIs are mounted at:

- `/admin_panel/`

So all endpoint paths below are relative to that base.

---

## 1) Platform Settings Endpoint

Source:

- View: `UpdatePlatformSettingsView`
- URL path: `/admin_panel/platform_settings/`

### GET /admin_panel/platform_settings/

Returns the current singleton platform settings.

Current response shape:

```json
{
  "base_exposure_limit": "500.00",
  "max_profit": "15000.00",
  "max_crs": "30.00",
  "minimum_stake": "1.00",
  "max_risk_tolerance": "3000.00",
  "global_max_risk_tolerance": "3000.00",
  "starting_coin_balance": "500.00"
}
```

Meaning of risk fields:

- `max_risk_tolerance`: default per-market limit used when a market does not have a custom limit.
- `global_max_risk_tolerance`: global ceiling. Per-market limits cannot exceed this value.

### PATCH /admin_panel/platform_settings/

Partial update. Only submitted fields are updated.

Supported fields:

- `base_exposure_limit`
- `max_profit`
- `max_crs`
- `minimum_stake`
- `max_risk_tolerance`
- `global_max_risk_tolerance`
- `starting_coin_balance`

All values are expected as decimal-like values (string or numeric).

#### Validation rules

- All numeric values must be valid decimals.
- No field can be negative.
- `max_risk_tolerance` must be less than or equal to `global_max_risk_tolerance`.

#### Example request

```json
{
  "max_risk_tolerance": "2200.00",
  "global_max_risk_tolerance": "3000.00"
}
```

#### Success response (200)

```json
{
  "success": true,
  "updated_fields": [
    "max_risk_tolerance",
    "global_max_risk_tolerance"
  ],
  "data": {
    "base_exposure_limit": "500.00",
    "max_profit": "15000.00",
    "max_crs": "30.00",
    "minimum_stake": "1.00",
    "max_risk_tolerance": "2200.00",
    "global_max_risk_tolerance": "3000.00",
    "starting_coin_balance": "500.00"
  }
}
```

#### Error responses

- `400` invalid decimal input:

```json
{
  "success": false,
  "error": "All values must be valid decimal numbers."
}
```

- `400` negative values:

```json
{
  "success": false,
  "error": "max_risk_tolerance cannot be negative."
}
```

- `400` per-market default above global ceiling:

```json
{
  "success": false,
  "error": "max_risk_tolerance cannot exceed global_max_risk_tolerance."
}
```

- `400` no usable fields:

```json
{
  "success": false,
  "error": "No valid fields provided for update."
}
```

---

## 2) Suspended Markets List Endpoint

Source:

- View: `SuspendedMarketsView`
- URL path: `/admin_panel/markets/suspended/`

### GET /admin_panel/markets/suspended/

Returns markets considered suspended by risk breach logic.

### Current inclusion logic

A market is included when:

- `net_exposure >= effective_per_market_limit`

Where:

- `net_exposure = abs(exposure_over - exposure_under)`
- `effective_per_market_limit = min(configured_per_market_limit, global_max_risk_tolerance)`
- `configured_per_market_limit = market.max_risk_tolerance` if set, otherwise platform `max_risk_tolerance`

Important behavior:

- Inclusion is exposure-threshold based, not only boolean-flag based.
- A market appears if it breaches its effective per-market limit, whether or not that value is below global.

### Response shape

```json
{
  "suspended_markets": [
    {
      "id": 101,
      "stock_symbol": "AAPL",
      "stock_url": "https://...",
      "stock_company_name": "Apple Inc",
      "target_price": "210.00",
      "expiry_date": "2026-03-27",
      "outcome_type": "over",
      "display_odds_over": "+105",
      "display_odds_under": "-120",
      "implied_odds_over": "0.4880",
      "implied_odds_under": "0.5450",
      "net_exposure": "2250.00",
      "configured_max_risk_tolerance": "2200.00",
      "per_market_max_risk_tolerance": "2200.00",
      "global_max_risk_tolerance": "3000.00",
      "net_exposure_percent_of_per_market_limit": "102.27",
      "net_exposure_percent_of_global_limit": "75.00",
      "is_active": true,
      "is_suspended_over": true,
      "is_suspended_under": false,
      "requires_admin_override": true,
      "nudge_offset_over": 0,
      "nudge_offset_under": 0
    }
  ]
}
```

Field notes:

- `configured_max_risk_tolerance`:
  - null means no market override; platform default is used.
- `per_market_max_risk_tolerance`:
  - effective limit after global cap is applied.
- `%` fields are returned as strings with 2 decimals.

---

## 3) Suspended Market Detail Endpoint

Source:

- View: `SuspendedMarketDetailView`
- URL path: `/admin_panel/markets/suspended/{market_id}/`

### GET /admin_panel/markets/suspended/{market_id}/

Returns the same market shape as an item in `suspended_markets` list.

### PATCH /admin_panel/markets/suspended/{market_id}/

Partial update endpoint for suspended-market controls.

Accepted patch fields:

- `is_active` (boolean)
- `is_suspended_over` (boolean)
- `is_suspended_under` (boolean)
- `requires_admin_override` (boolean)
- `max_risk_tolerance` (decimal or null)

`max_risk_tolerance` behavior:

- If set to a decimal, it becomes the market-specific configured limit.
- If set to `null`, market reverts to platform default `max_risk_tolerance`.
- Cannot be negative.
- Cannot exceed platform `global_max_risk_tolerance`.

Automatic resync behavior:

- If request includes `max_risk_tolerance` and does not include manual suspension flags (`is_suspended_over`, `is_suspended_under`, `requires_admin_override`), lock flags are auto-recomputed from current exposure and effective limit.
- If manual flags are sent in the same PATCH, those explicit values are honored for that request.

#### Example PATCH: set custom per-market limit

```json
{
  "max_risk_tolerance": "1800.00"
}
```

#### Example PATCH: reset to platform default

```json
{
  "max_risk_tolerance": null
}
```

#### Example PATCH: custom limit + manual flags

```json
{
  "max_risk_tolerance": "2000.00",
  "is_suspended_over": false,
  "is_suspended_under": false,
  "requires_admin_override": false
}
```

### Error responses

- `404` market not found:

```json
{
  "detail": "Market not found."
}
```

- `400` invalid boolean:

```json
{
  "is_suspended_over": "Invalid boolean value"
}
```

- `400` negative market limit:

```json
{
  "max_risk_tolerance": "max_risk_tolerance cannot be negative."
}
```

- `400` market limit above global ceiling:

```json
{
  "max_risk_tolerance": "Per-market max_risk_tolerance cannot exceed global_max_risk_tolerance."
}
```

---

## Integration Guidance for External Admin Frontend

1. Risk settings screen

- Show and edit both values from `/admin_panel/platform_settings/`:
  - `max_risk_tolerance` (default per-market)
  - `global_max_risk_tolerance` (hard ceiling)
- Enforce client-side `max_risk_tolerance <= global_max_risk_tolerance` before submit for better UX.

2. Suspended markets table

- Use `/admin_panel/markets/suspended/` as source of truth for risk-breached markets.
- Display these columns:
  - `net_exposure`
  - `configured_max_risk_tolerance`
  - `per_market_max_risk_tolerance`
  - `global_max_risk_tolerance`
  - `net_exposure_percent_of_per_market_limit`
  - `net_exposure_percent_of_global_limit`

3. Suspended market details/edit drawer

- Use `/admin_panel/markets/suspended/{market_id}/` PATCH for both:
  - manual lock flag controls
  - per-market limit updates

4. Important migration dependency

These DB fields must exist in the deployed environment:

- `Market.max_risk_tolerance`
- `PlatformSettings.global_max_risk_tolerance`

If missing, run migrations before integrating frontend changes.

---

## Security Note

Current permissions in code:

- Platform settings endpoint: `AllowAny`
- Suspended markets endpoints: `IsAdminUser`

For production hardening, platform settings should typically also be admin-protected.
