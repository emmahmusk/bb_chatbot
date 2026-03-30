# Admin Competition Endpoints API Contract

This document defines the API contract for admin-facing competition management endpoints.  
All endpoints are located in the `admin_panel` Django app and are intended for external admin frontend integration.

---

## Base Route

Admin panel APIs are mounted at:

```
/admin_panel/
```

So all paths below are relative to that base (e.g. full URL: `https://yourdomain.com/admin_panel/competitions/`).

---

## Authentication & Permissions

All four endpoints require the request user to be authenticated **and** pass the `IsAdmin` permission check.

A user is considered an admin if any of the following is true:

- `user.is_superuser` is `True`
- `user.is_staff` is `True`
- `user.profile.is_admin` is `True`
- `user.admin.role` is `"admin"` or `"superadmin"`

Unauthenticated or non-admin requests will receive:

```json
{ "detail": "Authentication credentials were not provided." }
```
> HTTP `401` for unauthenticated, `403` for authenticated but unauthorised.

---

## Endpoints

### 1. List All Competitions

```
GET /admin_panel/competitions/
```

Returns a paginated list of all competitions, ordered by most recently created.

#### Query Parameters

| Parameter   | Type   | Required | Description                                    |
|-------------|--------|----------|------------------------------------------------|
| `status`    | string | No       | Filter by status: `registration`, `active`, `completed`, `cancelled` |
| `search`    | string | No       | Case-insensitive search on competition `name`  |
| `page`      | int    | No       | Page number (default: `1`)                     |
| `page_size` | int    | No       | Results per page (default: `20`, max: `100`)   |

#### Example Request

```http
GET /admin_panel/competitions/?status=active&search=equity&page=1
Authorization: Bearer <admin_token>
```

#### Success Response — `200 OK`

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Good News Venture Equity Pool",
      "description": "Top performers win cash prizes.",
      "creator": 5,
      "creator_username": "emmahmusk",
      "max_members": 100,
      "member_count": 1,
      "start_date": "2026-03-30T05:00:00Z",
      "end_date": "2026-04-04T05:00:00Z",
      "registration_close_date": "2026-03-30T05:00:00Z",
      "status": "registration",
      "entry_fee": "100.00",
      "first_place_prize": "5000.00",
      "second_place_prize": "2500.00",
      "third_place_prize": "1000.00",
      "scoring_method": "total_payout",
      "is_private": false,
      "starting_coin_balance": "10000.00",
      "is_registration_open": true,
      "is_full": false,
      "user_joined": false,
      "created_at": "2026-03-29T18:00:00Z",
      "updated_at": "2026-03-29T18:00:00Z"
    }
  ]
}
```

---

### 2. Retrieve a Single Competition

```
GET /admin_panel/competitions/<id>/
```

Returns the full details of one competition by its `id`.

#### Path Parameters

| Parameter | Type | Description              |
|-----------|------|--------------------------|
| `id`      | int  | The competition's primary key |

#### Example Request

```http
GET /admin_panel/competitions/1/
Authorization: Bearer <admin_token>
```

#### Success Response — `200 OK`

Returns the same object shape as a single item in the list response above.

#### Error Response — `404 Not Found`

```json
{ "detail": "No Competition matches the given query." }
```

---

### 3. Update a Competition

```
PATCH /admin_panel/competitions/<id>/update/
```

Partially updates a competition. Only the fields you include in the request body will be changed.

#### Path Parameters

| Parameter | Type | Description              |
|-----------|------|--------------------------|
| `id`      | int  | The competition's primary key |

#### Writable Fields

| Field                    | Type    | Description                                          |
|--------------------------|---------|------------------------------------------------------|
| `name`                   | string  | Competition name                                     |
| `description`            | string  | Competition description                              |
| `status`                 | string  | One of: `registration`, `active`, `completed`, `cancelled` |
| `max_members`            | int     | Maximum number of participants                       |
| `start_date`             | datetime | ISO 8601 datetime                                   |
| `end_date`               | datetime | ISO 8601 datetime (must be after `start_date`)      |
| `registration_close_date`| datetime | ISO 8601 datetime (must be on or before `start_date`) |
| `entry_fee`              | decimal | Entry fee in dollars (e.g. `"50.00"`)                |
| `first_place_prize`      | decimal | 1st place cash prize in dollars                      |
| `second_place_prize`     | decimal | 2nd place cash prize in dollars                      |
| `third_place_prize`      | decimal | 3rd place cash prize in dollars                      |
| `scoring_method`         | string  | One of: `net_profit`, `roi`, `win_rate`, `total_payout` |
| `is_private`             | boolean | Whether the competition is invite-only               |
| `starting_coin_balance`  | decimal | Starting BBC coin balance awarded to each participant |

#### Example Request — Update status and prizes

```http
PATCH /admin_panel/competitions/1/update/
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "status": "active",
  "first_place_prize": "6000.00",
  "second_place_prize": "3000.00"
}
```

#### Success Response — `200 OK`

Returns the full updated competition object.

#### Validation Error Response — `400 Bad Request`

```json
{
  "end_date": ["end_date must be later than start_date."]
}
```

#### Error Response — `404 Not Found`

```json
{ "detail": "No Competition matches the given query." }
```

---

### 4. Delete a Competition

```
DELETE /admin_panel/competitions/<id>/delete/
```

Permanently deletes a competition and all of its related records (members, bets, etc.).  
**This action is irreversible.**

#### Path Parameters

| Parameter | Type | Description              |
|-----------|------|--------------------------|
| `id`      | int  | The competition's primary key |

#### Example Request

```http
DELETE /admin_panel/competitions/1/delete/
Authorization: Bearer <admin_token>
```

#### Success Response — `204 No Content`

```json
{
  "detail": "Competition 'Good News Venture Equity Pool' (id=1) has been deleted."
}
```

#### Error Response — `404 Not Found`

```json
{ "detail": "No Competition matches the given query." }
```

---

## Competition Object Reference

Full shape of the Competition object returned by all read endpoints:

| Field                    | Type     | Read-only | Notes                                              |
|--------------------------|----------|-----------|----------------------------------------------------|
| `id`                     | int      | ✅        | Auto-assigned primary key                          |
| `name`                   | string   |           |                                                    |
| `description`            | string   |           | Nullable                                           |
| `creator`                | int      | ✅        | User ID of creator                                 |
| `creator_username`       | string   | ✅        | Username of creator                                |
| `max_members`            | int      |           |                                                    |
| `member_count`           | int      | ✅        | Current number of joined members                   |
| `start_date`             | datetime |           | ISO 8601                                           |
| `end_date`               | datetime |           | ISO 8601                                           |
| `registration_close_date`| datetime |           | ISO 8601, nullable                                 |
| `status`                 | string   |           | `registration` / `active` / `completed` / `cancelled` |
| `entry_fee`              | decimal  |           | In dollars, `"0.00"` for free                      |
| `first_place_prize`      | decimal  |           | In dollars                                         |
| `second_place_prize`     | decimal  |           | In dollars                                         |
| `third_place_prize`      | decimal  |           | In dollars                                         |
| `scoring_method`         | string   |           | `net_profit` / `roi` / `win_rate` / `total_payout` |
| `is_private`             | boolean  |           |                                                    |
| `starting_coin_balance`  | decimal  |           | In BBC coins                                       |
| `is_registration_open`   | boolean  | ✅        | Computed from status + dates                       |
| `is_full`                | boolean  | ✅        | `member_count >= max_members`                      |
| `user_joined`            | boolean  | ✅        | Whether the requesting user has joined             |
| `created_at`             | datetime | ✅        | ISO 8601                                           |
| `updated_at`             | datetime | ✅        | ISO 8601                                           |

---

## Status Values Reference

| Status         | Meaning                                  |
|----------------|------------------------------------------|
| `registration` | Competition is open for registration     |
| `active`       | Competition is live / in progress        |
| `completed`    | Competition has ended and is finalised   |
| `cancelled`    | Competition was cancelled                |

---

## Scoring Method Values Reference

| Value         | Description                       |
|---------------|-----------------------------------|
| `net_profit`  | Ranked by total net profit/loss   |
| `roi`         | Ranked by Return on Investment (%) |
| `win_rate`    | Ranked by Win Rate (%)            |
| `total_payout`| Ranked by total payout received   |

---

## Integration Notes

1. **Authentication**: Use a JWT Bearer token from the `/admin_panel/login/` endpoint.
2. **Pagination**: Use `page` and `page_size` query params on the list endpoint. Check `next` and `previous` for navigation.
3. **Filtering**: Combine `status` and `search` on the list endpoint for admin dashboards with a search bar and status dropdown.
4. **Partial updates**: `PATCH` only — never `PUT`. Include only the fields you want to change.
5. **Deletion safety**: Consider presenting a confirmation dialog in the frontend before calling the delete endpoint, as it is irreversible.
6. **Prize display**: Prizes (`first_place_prize`, `second_place_prize`, `third_place_prize`) are returned as decimal strings (e.g. `"5000.00"`). Display with a `$` prefix in the UI.
7. **Starting balance**: `starting_coin_balance` is in BBC coins — display with a ` BBC` suffix.
