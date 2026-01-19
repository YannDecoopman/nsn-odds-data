# API Documentation - nsn-odds-data

Microservice REST pour récupérer les cotes de paris sportifs via Odds-API.io.

**Base URL:** `http://localhost:8002`

---

## Authentification

Si activée (`API_KEY_ENABLED=true`), toutes les requêtes doivent inclure le header :

```
X-API-Key: your-api-key
```

---

## Endpoints

### Events

#### Liste des événements
```
GET /events
```

Récupère la liste des événements sportifs avec filtres.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `sport` | string | Filtre par sport (ex: `football`) |
| `league` | string | Filtre par ligue |
| `status` | enum | `not_started`, `in_progress`, `ended` |
| `date_from` | string | Date début (YYYY-MM-DD) |
| `date_to` | string | Date fin (YYYY-MM-DD) |
| `limit` | int | Limite (max 2000, défaut 100) |
| `offset` | int | Décalage pagination |

**Response:**
```json
{
  "data": [
    {
      "id": "evt_123",
      "home": "Manchester United",
      "away": "Liverpool",
      "date": "2026-01-20T15:00:00Z",
      "status": "not_started",
      "sport": {"name": "Football", "slug": "football"},
      "league": {"name": "Premier League", "slug": "premier-league"}
    }
  ],
  "pagination": {"total": 150, "limit": 100, "offset": 0}
}
```

---

#### Événement par ID
```
GET /events/{event_id}
```

Récupère un événement spécifique.

**Response:**
```json
{
  "id": "evt_123",
  "home": "Manchester United",
  "away": "Liverpool",
  "date": "2026-01-20T15:00:00Z",
  "status": "not_started",
  "sport": {"name": "Football", "slug": "football"},
  "league": {"name": "Premier League", "slug": "premier-league"}
}
```

**Errors:** `404` si non trouvé

---

#### Événements en direct
```
GET /events/live
```

Récupère les matchs en cours avec scores.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `sport` | string | Filtre par sport |
| `limit` | int | Limite (max 100, défaut 20) |

**Response:**
```json
{
  "data": [
    {
      "id": "evt_456",
      "home": "Barcelona",
      "away": "Real Madrid",
      "date": "2026-01-18T20:00:00Z",
      "status": "in_progress",
      "scores": {"home": 2, "away": 1},
      "minute": 67,
      "period": "2H",
      "sport": {"name": "Football", "slug": "football"},
      "league": {"name": "La Liga", "slug": "la-liga"}
    }
  ]
}
```

---

#### Recherche d'événements
```
GET /events/search
```

Recherche par nom d'équipe.

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `q` | string | ✅ | Terme de recherche (min 2 caractères) |
| `sport` | string | | Sport (défaut: `football`) |
| `limit` | int | | Limite (max 50, défaut 10) |

---

#### Événements à venir
```
GET /events/upcoming
```

Événements des 7 prochains jours pour les ligues majeures (cache 1h).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `leagues` | string | Liste de ligues séparées par virgule |
| `limit` | int | Limite (max 200, défaut 50) |
| `offset` | int | Décalage pagination |

---

### Odds (Cotes)

#### Cotes d'un événement
```
GET /odds
```

Récupère les cotes pour un événement.

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `eventId` | string | ✅ | ID de l'événement |
| `market` | enum | | `1x2`, `asian_handicap`, `totals`, `btts`, `correct_score`, `double_chance` |
| `bookmakers` | string | | Liste séparée par virgule |

**Response (1x2):**
```json
{
  "event": {
    "id": "evt_123",
    "sport": "football",
    "league": "Premier League",
    "home_team": "Manchester United",
    "away_team": "Liverpool",
    "commence_time": "2026-01-20T15:00:00Z"
  },
  "market": "1x2",
  "bookmakers": [
    {
      "key": "bet365",
      "name": "Bet365",
      "odds": {"home": 2.10, "draw": 3.40, "away": 3.20},
      "updated_at": "2026-01-18T10:00:00Z"
    }
  ],
  "metadata": {
    "generated_at": "2026-01-18T10:05:00Z",
    "is_ended": false
  }
}
```

---

#### Cotes batch (multi-événements)
```
GET /odds/multi
```

Récupère les cotes pour plusieurs événements en une requête. Économise le quota API.

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `eventIds` | string | ✅ | IDs séparés par virgule (max 10) |
| `market` | enum | | Type de marché |
| `bookmakers` | string | | Liste de bookmakers |

**Response:** Array d'objets odds (même format que `/odds`)

**Errors:** `400` si plus de 10 IDs ou liste vide

---

#### Cotes modifiées
```
GET /odds/updated
```

Récupère uniquement les cotes modifiées depuis un timestamp. Utile pour le polling efficace.

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `since` | int | ✅ | Timestamp Unix (secondes) |
| `bookmaker` | string | | Filtre bookmaker |
| `sport` | string | | Filtre sport |
| `market` | string | | Type de marché (défaut: `ML`) |

**Response:**
```json
[
  {
    "eventId": "evt_123",
    "bookmaker": "Bet365",
    "market": "ML",
    "odds": {"home": 2.15, "draw": 3.30, "away": 3.25},
    "updatedAt": "2026-01-18T10:15:00Z"
  }
]
```

---

#### Historique des mouvements
```
GET /odds/movements
```

Récupère l'historique des variations de cotes.

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `eventId` | string | ✅ | ID de l'événement |
| `bookmaker` | string | | Bookmaker (défaut: premier configuré) |
| `market` | string | | Type de marché (défaut: `ML`) |

**Response:**
```json
{
  "eventId": "evt_123",
  "bookmaker": "Bet365",
  "market": "ML",
  "opening": {"home": 2.20, "draw": 3.50, "away": 3.10, "timestamp": "2026-01-15T10:00:00Z"},
  "latest": {"home": 2.10, "draw": 3.40, "away": 3.20, "timestamp": "2026-01-18T10:00:00Z"},
  "movements": [
    {"home": 2.20, "draw": 3.50, "away": 3.10, "timestamp": "2026-01-15T10:00:00Z"},
    {"home": 2.15, "draw": 3.45, "away": 3.15, "timestamp": "2026-01-16T10:00:00Z"},
    {"home": 2.10, "draw": 3.40, "away": 3.20, "timestamp": "2026-01-18T10:00:00Z"}
  ]
}
```

---

### Value Bets

#### Liste des value bets
```
GET /value-bets
```

Détecte les paris à valeur positive (expected value > seuil).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `sport` | string | Filtre par sport |
| `league` | string | Filtre par ligue |
| `minEv` | float | EV minimum (défaut: 2.0%) |
| `limit` | int | Limite (max 50, défaut 10) |

**Response:**
```json
{
  "data": [
    {
      "id": "vb_123_bet365",
      "eventId": "123",
      "bookmaker": "Bet365",
      "market": "ML",
      "betSide": "home",
      "expectedValue": 5.5,
      "expectedValueUpdatedAt": "2026-01-18T10:00:00Z",
      "bookmakerOdds": {"home": 2.10, "draw": 3.40, "away": 3.80},
      "consensusOdds": {"home": 1.95, "draw": 3.50, "away": 4.00},
      "event": {
        "home": "Team A",
        "away": "Team B",
        "date": "2026-01-20T15:00:00Z",
        "sport": {"name": "Football", "slug": "football"},
        "league": {"name": "Premier League", "slug": "premier-league"}
      }
    }
  ]
}
```

---

### Arbitrage

#### Opportunités d'arbitrage
```
GET /arbitrage-bets
```

Détecte les opportunités d'arbitrage entre bookmakers.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `sport` | string | Filtre par sport |
| `minProfit` | float | Profit minimum (défaut: 1.0%) |
| `limit` | int | Limite (max 20, défaut 5) |

**Response:**
```json
{
  "data": [
    {
      "id": "arb_456",
      "eventId": "456",
      "market": "ML",
      "profitMargin": 2.5,
      "impliedProbability": 97.5,
      "totalStake": 100,
      "legs": [
        {"side": "home", "bookmaker": "Bet365", "odds": 2.10, "directLink": "https://..."},
        {"side": "away", "bookmaker": "Betano", "odds": 2.20, "directLink": "https://..."}
      ],
      "optimalStakes": [
        {"side": "home", "bookmaker": "Bet365", "stake": 51.2, "potentialReturn": 107.52},
        {"side": "away", "bookmaker": "Betano", "stake": 48.8, "potentialReturn": 107.36}
      ],
      "event": {...},
      "detectedAt": "2026-01-18T12:00:00Z"
    }
  ]
}
```

---

### Sports

#### Liste des sports
```
GET /sports
```

Récupère les sports disponibles.

**Response:**
```json
[
  {"key": "football", "title": "Football", "active": true},
  {"key": "basketball", "title": "Basketball", "active": true},
  {"key": "tennis", "title": "Tennis", "active": true}
]
```

---

### Bookmakers

#### Liste des bookmakers
```
GET /bookmakers
```

Récupère les bookmakers disponibles.

**Response:**
```json
[
  {"key": "bet365", "name": "Bet365", "region": "uk", "is_active": true},
  {"key": "betano", "name": "Betano", "region": "br", "is_active": true}
]
```

---

### Leagues

#### Liste des ligues
```
GET /leagues
```

Récupère les ligues disponibles.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `sport` | string | Filtre par sport |

**Response:**
```json
{
  "data": [
    {"name": "Premier League", "slug": "premier-league", "sport": "football"},
    {"name": "La Liga", "slug": "la-liga", "sport": "football"}
  ]
}
```

---

### Participants (Équipes)

#### Liste des participants
```
GET /participants
```

Récupère les équipes/participants.

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `sport` | string | ✅ | Sport (ex: `football`) |
| `search` | string | | Recherche par nom |
| `limit` | int | | Limite (max 500, défaut 100) |
| `offset` | int | | Décalage pagination |

**Response:**
```json
{
  "data": [
    {
      "id": "p1",
      "name": "Manchester United",
      "slug": "manchester-united",
      "sport": "football",
      "country": "England",
      "logo": "https://..."
    }
  ],
  "total": 250
}
```

---

#### Participant par ID
```
GET /participants/{participant_id}
```

Récupère un participant spécifique.

**Response:**
```json
{
  "id": "p1",
  "name": "Manchester United",
  "slug": "manchester-united",
  "sport": "football",
  "country": "England",
  "logo": "https://..."
}
```

**Errors:** `404` si non trouvé

---

### System

#### Health check
```
GET /health
```

**Response:**
```json
{"status": "healthy", "service": "nsn-odds-data"}
```

---

#### Métriques
```
GET /metrics
```

Récupère les statistiques d'utilisation.

**Response:**
```json
{
  "requests_total": 1500,
  "errors_total": 12,
  "avg_latency_ms": 45.2,
  "cache_hits": 800,
  "cache_misses": 200,
  "api_calls": 400
}
```

---

## Codes d'erreur

| Code | Description |
|------|-------------|
| `400` | Bad Request - paramètres invalides |
| `401` | Unauthorized - API key manquante/invalide |
| `404` | Not Found - ressource non trouvée |
| `422` | Validation Error - paramètres requis manquants |
| `429` | Rate Limit - trop de requêtes |
| `502` | Bad Gateway - erreur provider externe |
| `504` | Gateway Timeout - timeout provider |

**Format erreur:**
```json
{
  "error": "ERROR_CODE",
  "message": "Description de l'erreur",
  "details": {}
}
```

---

## Rate Limiting

| Type | Limite |
|------|--------|
| Endpoints standard | 60/minute |
| Endpoints lourds (`/odds/multi`, `/value-bets`) | 10/minute |
| Recherche | 30/minute |

---

## Configuration

| Variable | Description | Défaut |
|----------|-------------|--------|
| `ODDS_API_KEY` | Clé API Odds-API.io | - |
| `DEFAULT_BOOKMAKERS` | Bookmakers par défaut | `betano,sportingbet,betfair,bet365` |
| `API_KEY_ENABLED` | Activer auth API key | `false` |
| `API_KEY` | Clé pour authentification | - |
