# API Reference - nsn-odds-data

Base URL: `http://localhost:8002`

## Health & Info

### GET /health

Health check endpoint.

**Response**
```json
{
  "status": "healthy",
  "service": "nsn-odds-data"
}
```

### GET /sports

List available sports.

**Response**
```json
[
  {
    "key": "football",
    "title": "Football",
    "active": true
  }
]
```

### GET /bookmakers

List configured bookmakers.

**Response**
```json
[
  {
    "key": "Bet365",
    "name": "Bet365",
    "region": "br",
    "is_active": true
  }
]
```

---

## Events

### GET /events

List events with filters and pagination.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sport` | string | - | Filter by sport slug (e.g., `football`) |
| `league` | string | - | Filter by league slug |
| `status` | enum | - | Filter by status: `not_started`, `in_progress`, `ended` |
| `date_from` | string | - | Start date (ISO 8601) |
| `date_to` | string | - | End date (ISO 8601) |
| `limit` | int | 20 | Max results (1-100) |
| `offset` | int | 0 | Pagination offset |

**Example Request**
```bash
curl "http://localhost:8002/events?sport=football&limit=5&offset=0"
```

**Response**
```json
{
  "data": [
    {
      "id": "67426068",
      "home": "AL Najaf",
      "away": "AL Naft Maysan",
      "date": "2026-01-14T14:30:00Z",
      "status": "not_started",
      "scores": null,
      "sport": {
        "name": "Football",
        "slug": "football"
      },
      "league": {
        "name": "Iraq - Iraqi League",
        "slug": "iraq-iraqi-league"
      }
    }
  ],
  "pagination": {
    "total": 8828,
    "limit": 5,
    "offset": 0
  }
}
```

---

### GET /events/live

List live events with scores. Cached for 30 seconds.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sport` | string | - | Filter by sport slug |
| `limit` | int | 20 | Max results (1-100) |

**Example Request**
```bash
curl "http://localhost:8002/events/live?sport=football"
```

**Response**
```json
{
  "data": [
    {
      "id": "67426068",
      "home": "AL Najaf",
      "away": "AL Naft Maysan",
      "date": "2026-01-14T14:30:00Z",
      "status": "in_progress",
      "scores": {
        "home": 2,
        "away": 1
      },
      "sport": {
        "name": "Football",
        "slug": "football"
      },
      "league": {
        "name": "Iraq - Iraqi League",
        "slug": "iraq-iraqi-league"
      },
      "minute": 67,
      "period": "2H"
    }
  ]
}
```

---

## Leagues

### GET /leagues

List available leagues.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sport` | string | - | Filter by sport slug |

**Example Request**
```bash
curl "http://localhost:8002/leagues?sport=football"
```

**Response**
```json
{
  "data": [
    {
      "name": "England - Premier League",
      "slug": "england-premier-league",
      "sport": "football"
    },
    {
      "name": "Spain - La Liga",
      "slug": "spain-la-liga",
      "sport": "football"
    }
  ]
}
```

---

## Odds

### GET /odds

Get odds for a specific event.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `eventId` | string | **required** | Event ID |
| `market` | string | `1x2` | Market type: `1x2`, `asian_handicap`, `totals` |
| `bookmakers` | string | config | Comma-separated bookmaker keys |

**Example Request - 1x2 (Match Line)**
```bash
curl "http://localhost:8002/odds?eventId=67426068&market=1x2"
```

**Response (1x2)**
```json
{
  "event": {
    "id": "67426068",
    "sport": "football",
    "league": "Iraq - Iraqi League",
    "league_id": null,
    "home_team": "AL Najaf",
    "away_team": "AL Naft Maysan",
    "commence_time": "2026-01-14T14:30:00Z"
  },
  "market": "1x2",
  "bookmakers": [
    {
      "key": "bet365",
      "name": "Bet365",
      "odds": {
        "home": 1.85,
        "draw": 3.40,
        "away": 4.20
      },
      "updated_at": "2026-01-14T14:00:00Z"
    }
  ],
  "metadata": {
    "generated_at": "2026-01-14T14:05:00",
    "is_ended": false,
    "hash": ""
  }
}
```

---

**Example Request - Totals (Over/Under)**
```bash
curl "http://localhost:8002/odds?eventId=64055555&market=totals"
```

**Response (Totals)**
```json
{
  "event": {
    "id": "64055555",
    "sport": "football",
    "league": "Saudi Arabia - Saudi Pro League",
    "league_id": null,
    "home_team": "Al Qadsiah",
    "away_team": "Al-Fayha FC",
    "commence_time": "2026-01-14T14:45:00Z"
  },
  "market": "totals",
  "bookmakers": [
    {
      "key": "bet365",
      "name": "Bet365",
      "lines": [
        {
          "line": 2.5,
          "over": 1.85,
          "under": 1.95
        },
        {
          "line": 3.0,
          "over": 2.10,
          "under": 1.70
        },
        {
          "line": 3.5,
          "over": 2.50,
          "under": 1.50
        }
      ],
      "updated_at": "2026-01-14T14:00:00Z"
    }
  ],
  "metadata": {
    "generated_at": "2026-01-14T14:05:00",
    "is_ended": false,
    "hash": ""
  }
}
```

---

**Example Request - Asian Handicap**
```bash
curl "http://localhost:8002/odds?eventId=67426068&market=asian_handicap"
```

**Response (Asian Handicap)**
```json
{
  "event": {
    "id": "67426068",
    "sport": "football",
    "league": "Iraq - Iraqi League",
    "league_id": null,
    "home_team": "AL Najaf",
    "away_team": "AL Naft Maysan",
    "commence_time": "2026-01-14T14:30:00Z"
  },
  "market": "asian_handicap",
  "bookmakers": [
    {
      "key": "bet365",
      "name": "Bet365",
      "lines": [
        {
          "hdp": -0.5,
          "home": 1.90,
          "away": 1.90
        },
        {
          "hdp": -1.0,
          "home": 2.20,
          "away": 1.65
        }
      ],
      "updated_at": "2026-01-14T14:00:00Z"
    }
  ],
  "metadata": {
    "generated_at": "2026-01-14T14:05:00",
    "is_ended": false,
    "hash": ""
  }
}
```

---

## Static Files

### POST /generate

Request generation of a static odds file. Used for caching and CDN delivery.

**Request Body**
```json
{
  "event_id": "67426068",
  "market": "1x2",
  "bookmakers": ["Bet365", "Betano"]
}
```

**Response**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "path": "2026/01/odds-67426068-abc123.json"
}
```

### GET /files/{request_id}

Get status of a generated file.

**Response**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "path": "2026/01/odds-67426068-abc123.json",
  "hash": "abc123def456",
  "updated_at": "2026-01-14T14:05:00Z"
}
```

### GET /static/{year}/{month}/{filename}

Serve generated static JSON files.

**Example**
```bash
curl "http://localhost:8002/static/2026/01/odds-67426068-abc123.json"
```

---

## Error Responses

All endpoints return standard HTTP error codes:

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Invalid request body |
| 500 | Internal Server Error |

**Error Response Format**
```json
{
  "detail": "Error message here"
}
```

---

## Caching

| Endpoint | Cache TTL |
|----------|-----------|
| `/sports` | 24 hours |
| `/leagues` | 24 hours |
| `/events` | 5 minutes |
| `/events/live` | 30 seconds |
| `/odds` | No cache |

---

## Rate Limits

This API proxies Odds-API.io. Rate limits depend on your Odds-API.io plan.
