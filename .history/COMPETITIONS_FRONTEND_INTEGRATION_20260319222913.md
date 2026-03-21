# Competition Endpoints - Frontend Integration Guide

## Simple explanation first

When I said lightweight frontend integration contract, I meant:
- A clear list of API endpoints your Flutter page should call.
- The exact request body to send.
- The exact response shape to expect.
- Common error cases to handle.

So your frontend can integrate quickly without guessing backend behavior.

## Base URL

All competition endpoints are under:
- /bet/competitions/

Reason:
- core URL config mounts betengine under /bet/
- competition routes are inside betengine urls

## Authentication rules

- Public (no token required):
1. GET /bet/competitions/
2. GET /bet/competitions/{competition_id}/
3. GET /bet/competitions/{competition_id}/leaderboard/

- Auth required (JWT Bearer token):
1. POST /bet/competitions/
2. POST /bet/competitions/{competition_id}/join/
3. GET /bet/competitions/my/

## 1) List competitions

Endpoint:
- GET /bet/competitions/

Purpose:
- Show discover/browse page (similar to your attached public leagues layout)

Query params (optional):
- status: registration | active | completed | cancelled
- q: text search on name/description
- registration_open: true | 1 | yes
- ordering: created_at | -created_at | start_date | -start_date | end_date | -end_date
- page: number
- page_size: number (max 100)

Example:
GET /bet/competitions/?status=registration&registration_open=true&ordering=start_date&page=1&page_size=20

Success response (paginated):
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 7,
      "name": "Tech Titans April",
      "description": "Predict top tech movers for April",
      "creator": 12,
      "creator_username": "admin_user",
      "max_members": 50,
      "member_count": 18,
      "start_date": "2026-04-01T00:00:00Z",
      "end_date": "2026-04-30T23:59:59Z",
      "registration_close_date": "2026-03-31T23:59:59Z",
      "status": "registration",
      "entry_fee": "10.00",
      "scoring_method": "net_profit",
      "is_private": false,
      "is_registration_open": true,
      "is_full": false,
      "user_joined": false,
      "created_at": "2026-03-18T10:00:00Z",
      "updated_at": "2026-03-18T10:00:00Z"
    }
  ]
}
```

## 2) Create competition

Endpoint:
- POST /bet/competitions/

Auth:
- Required

Request body:
```json
{
  "name": "Small Caps Challenge",
  "description": "Community stock prediction challenge for small caps",
  "max_members": 50,
  "start_date": "2026-04-10T00:00:00Z",
  "end_date": "2026-05-10T23:59:59Z",
  "registration_close_date": "2026-04-09T23:59:59Z",
  "entry_fee": "0.00",
  "scoring_method": "net_profit",
  "is_private": false
}
```

Important validations:
- end_date must be later than start_date
- registration_close_date must be on/before start_date

Success response:
- 201 Created
- returns full competition payload (same shape as list item)

Common error response:
- 400 Bad Request
```json
{
  "end_date": ["end_date must be later than start_date."]
}
```

## 3) Competition detail

Endpoint:
- GET /bet/competitions/{competition_id}/

Purpose:
- Competition detail page before user clicks Join

Success response:
- 200 OK
- same competition object shape as list item

Not found:
- 404
```json
{
  "detail": "Not found."
}
```

## 4) Join competition

Endpoint:
- POST /bet/competitions/{competition_id}/join/

Auth:
- Required

Request body:
- Empty body is fine

Backend behavior:
- Checks competition exists
- Auto-updates status by date
- Prevents duplicate join
- Rejects if registration closed
- Rejects if full
- If entry_fee > 0, debits user coin balance
- Creates CompetitionMember row

Success response:
- 201 Created
```json
{
  "competition_id": 7,
  "joined": true,
  "current_member_count": 19,
  "max_members": 50,
  "message": "Successfully joined competition."
}
```

Already joined response:
- 200 OK
```json
{
  "competition_id": 7,
  "joined": true,
  "current_member_count": 19,
  "max_members": 50,
  "message": "You already joined this competition."
}
```

Common error responses:
- 400 closed
```json
{
  "error": "Registration is closed for this competition."
}
```

- 400 full
```json
{
  "error": "Competition is full."
}
```

- 400 insufficient balance
```json
{
  "error": "Insufficient coin balance for entry fee."
}
```

- 404 missing competition
```json
{
  "error": "Competition not found."
}
```

## 5) Leaderboard

Endpoint:
- GET /bet/competitions/{competition_id}/leaderboard/

Purpose:
- Show rankings and performance metrics

Response (paginated):
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 301,
      "user": 55,
      "username": "trader_alpha",
      "joined_at": "2026-03-20T08:00:00Z",
      "final_rank": null,
      "final_score": null,
      "total_bets": 14,
      "net_profit": 128.55,
      "roi": 12.44,
      "win_rate": 57.14
    }
  ]
}
```

## 6) My competitions

Endpoint:
- GET /bet/competitions/my/

Auth:
- Required

Purpose:
- User profile page showing competitions user joined

Response (paginated):
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 301,
      "competition": 7,
      "competition_name": "Tech Titans April",
      "user": 55,
      "username": "trader_alpha",
      "joined_at": "2026-03-20T08:00:00Z",
      "final_rank": null,
      "final_score": null,
      "is_disqualified": false
    }
  ]
}
```

## Enum values to use in frontend

Competition status:
- registration
- active
- completed
- cancelled

Scoring method:
- net_profit
- roi
- win_rate
- total_payout

## Flutter integration notes

Recommended page flow:
1. Discover page:
- call GET /bet/competitions/?status=registration&registration_open=true
- render cards/list with member_count/max_members and Join button

2. Detail page:
- call GET /bet/competitions/{id}/
- show dates, scoring method, entry fee, member capacity

3. Join action:
- POST /bet/competitions/{id}/join/
- handle 201 success and 200 already-joined as successful UX states
- handle 400/404 errors with snackbars/dialogs

4. Leaderboard tab:
- GET /bet/competitions/{id}/leaderboard/

5. My competitions page:
- GET /bet/competitions/my/

JWT header example:
- Authorization: Bearer <access_token>

## Suggested UI labels

- Join: enabled when is_registration_open=true and is_full=false and user_joined=false
- Joined: when user_joined=true
- Full: when is_full=true
- Closed: when is_registration_open=false

## Quick error handling map for frontend

- 401: token missing/expired, send user to login
- 404: competition not found, pop page and refresh list
- 400: business rule failure, show backend error message

## Notes

- Pagination follows DRF PageNumberPagination (count, next, previous, results)
- entry_fee is string-decimal in competition payload
- Financial values should be parsed as decimal-safe in frontend
