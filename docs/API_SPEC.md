# Spec API REST - Adaptation pour Plugin WordPress

## Contexte

L'API actuelle (`nsn-odds-data-api`) supporte :
- `GET /events` - Liste événements
- `POST /generate` - Génère fichier JSON odds
- `GET /static/{path}` - Sert fichiers générés
- Marché 1x2 uniquement

**Bonne nouvelle** : Odds-API.io (source) fournit déjà :
- `/events/live` - événements en cours avec scores
- Tous les marchés (Asian Handicap, Totals, BTTS, Correct Score)
- `/odds/movements` - historique des cotes
- `/value-bets` - value bets détectés
- `/arbitrage-bets` - opportunités d'arbitrage
- WebSocket pour temps réel

**Notre rôle** : Proxy intelligent avec caching Redis, génération fichiers statiques, adaptation format WordPress.

**Référence API source** : https://docs.odds-api.io/llms-full.txt

Le plugin WordPress a besoin de 18 blocs avec des besoins spécifiques.

---

## Nouveaux Endpoints Requis

### 1. Events & Navigation

#### `GET /events`
**Amélioration de l'existant**

Query params :
- `sport` : string (filter par sport)
- `league` : string (filter par ligue slug)
- `status` : `not_started` | `in_progress` | `ended`
- `date_from` : ISO date
- `date_to` : ISO date
- `limit` : int (default 20, max 100)
- `offset` : int (pagination)

Response :
```json
{
  "data": [
    {
      "id": "67742382",
      "home": "Mexico",
      "away": "France",
      "homeId": 12345,
      "awayId": 67890,
      "date": "2026-01-13T21:00:00Z",
      "status": "not_started",
      "scores": null,
      "sport": { "name": "Football", "slug": "football" },
      "league": { "name": "Kings World Cup", "slug": "kings-world-cup" },
      "matchday": 5
    }
  ],
  "pagination": { "total": 150, "limit": 20, "offset": 0 }
}
```

---

#### `GET /events/live`
**Nouveau** - Liste événements en cours

Query params :
- `sport` : string (optionnel)
- `limit` : int (default 20)

Response :
```json
{
  "data": [
    {
      "id": "67742382",
      "home": "Mexico",
      "away": "France",
      "date": "2026-01-13T21:00:00Z",
      "status": "in_progress",
      "scores": { "home": 2, "away": 1 },
      "minute": 67,
      "period": "2H",
      "sport": { "name": "Football", "slug": "football" },
      "league": { "name": "Kings World Cup", "slug": "kings-world-cup" }
    }
  ]
}
```

---

#### `GET /events/search`
**Nouveau** - Recherche événements

Query params :
- `q` : string (min 2 chars, recherche équipes)
- `sport` : string (optionnel)
- `limit` : int (default 10)

Response : même format que `/events`

---

#### `GET /leagues`
**Nouveau** - Liste ligues disponibles

Query params :
- `sport` : string (optionnel)

Response :
```json
{
  "data": [
    { "name": "Premier League", "slug": "premier-league", "sport": "football" },
    { "name": "NBA", "slug": "nba", "sport": "basketball" }
  ]
}
```

---

### 2. Odds Data

#### `GET /odds`
**Amélioration majeure** - Cotes multi-marchés

Query params :
- `eventId` : string (requis)
- `market` : string (default "ML")
  - `ML` = Match Line (1X2)
  - `Asian Handicap`
  - `Totals` = Over/Under
  - `Both Teams to Score`
  - `Correct Score`
  - `Double Chance`
- `bookmakers` : string (liste comma-separated, optionnel)

Response ML :
```json
{
  "id": "67742382",
  "home": "Mexico",
  "away": "France",
  "date": "2026-01-13T21:00:00Z",
  "status": "not_started",
  "sport": { "name": "Football", "slug": "football" },
  "league": { "name": "Kings World Cup", "slug": "kings-world-cup" },
  "bookmakers": {
    "bet365": [
      {
        "name": "ML",
        "updatedAt": "2026-01-13T20:45:00Z",
        "odds": { "home": 1.53, "draw": 9.00, "away": 3.00 }
      }
    ]
  }
}
```

Response Asian Handicap :
```json
{
  "bookmakers": {
    "bet365": [
      {
        "name": "Asian Handicap",
        "updatedAt": "...",
        "odds": [
          { "hdp": -0.5, "home": 1.85, "away": 2.05 },
          { "hdp": -1.0, "home": 2.10, "away": 1.80 }
        ]
      }
    ]
  }
}
```

Response Totals (Over/Under) :
```json
{
  "bookmakers": {
    "bet365": [
      {
        "name": "Totals",
        "updatedAt": "...",
        "odds": [
          { "line": 2.5, "over": 1.90, "under": 1.95 },
          { "line": 3.5, "over": 2.50, "under": 1.55 }
        ]
      }
    ]
  }
}
```

Response BTTS :
```json
{
  "bookmakers": {
    "bet365": [
      {
        "name": "Both Teams to Score",
        "updatedAt": "...",
        "odds": { "yes": 1.75, "no": 2.05 }
      }
    ]
  }
}
```

Response Correct Score :
```json
{
  "bookmakers": {
    "bet365": [
      {
        "name": "Correct Score",
        "updatedAt": "...",
        "odds": [
          { "score": "1-0", "odds": 6.50 },
          { "score": "2-1", "odds": 8.50 },
          { "score": "Other", "odds": 25.00 }
        ]
      }
    ]
  }
}
```

Response Double Chance :
```json
{
  "bookmakers": {
    "bet365": [
      {
        "name": "Double Chance",
        "updatedAt": "...",
        "odds": { "1X": 1.25, "X2": 1.85, "12": 1.15 }
      }
    ]
  }
}
```

---

#### `GET /odds/movements`
**Nouveau** - Historique mouvements de cotes

Query params :
- `eventId` : string (requis)
- `bookmaker` : string (optionnel, default = premier dispo)
- `market` : string (default "ML")

Response :
```json
{
  "eventId": "67742382",
  "bookmaker": "bet365",
  "market": "ML",
  "opening": {
    "home": 1.80, "draw": 3.50, "away": 4.20,
    "timestamp": "2026-01-10T12:00:00Z"
  },
  "latest": {
    "home": 1.53, "draw": 9.00, "away": 3.00,
    "timestamp": "2026-01-13T20:45:00Z"
  },
  "movements": [
    { "home": 1.80, "draw": 3.50, "away": 4.20, "timestamp": "2026-01-10T12:00:00Z" },
    { "home": 1.75, "draw": 3.60, "away": 4.00, "timestamp": "2026-01-11T09:00:00Z" },
    { "home": 1.53, "draw": 9.00, "away": 3.00, "timestamp": "2026-01-13T20:45:00Z" }
  ]
}
```

---

### 3. Analysis Endpoints

#### `GET /value-bets`
**Nouveau** - Value bets détectés

Query params :
- `sport` : string (optionnel)
- `league` : string (optionnel)
- `minEV` : float (default 2.0)
- `limit` : int (default 10)

Response :
```json
{
  "data": [
    {
      "id": "vb_123456",
      "eventId": "67742382",
      "bookmaker": "bet365",
      "market": "ML",
      "betSide": "home",
      "expectedValue": 5.2,
      "expectedValueUpdatedAt": "2026-01-13T20:45:00Z",
      "bookmakerOdds": {
        "home": 2.10, "draw": 3.40, "away": 3.20,
        "homeDirectLink": "https://bet365.com/..."
      },
      "consensusOdds": { "home": 1.95, "draw": 3.50, "away": 3.30 },
      "event": {
        "home": "Mexico",
        "away": "France",
        "date": "2026-01-13T21:00:00Z",
        "sport": { "name": "Football" },
        "league": { "name": "Kings World Cup" }
      }
    }
  ]
}
```

---

#### `GET /arbitrage-bets`
**Nouveau** - Opportunités d'arbitrage

Query params :
- `sport` : string (optionnel)
- `minProfit` : float (default 1.0)
- `limit` : int (default 5)

Response :
```json
{
  "data": [
    {
      "id": "arb_789012",
      "eventId": "67742382",
      "market": "ML",
      "profitMargin": 2.3,
      "impliedProbability": 97.7,
      "totalStake": 100,
      "legs": [
        { "side": "home", "bookmaker": "bet365", "odds": 2.15, "directLink": "..." },
        { "side": "draw", "bookmaker": "pinnacle", "odds": 3.60, "directLink": "..." },
        { "side": "away", "bookmaker": "betfair", "odds": 3.50, "directLink": "..." }
      ],
      "optimalStakes": [
        { "side": "home", "bookmaker": "bet365", "stake": 46.51, "potentialReturn": 100.00 }
      ],
      "event": {
        "home": "Mexico", "away": "France",
        "date": "2026-01-13T21:00:00Z",
        "sport": { "name": "Football" },
        "league": { "name": "Kings World Cup" }
      },
      "detectedAt": "2026-01-13T20:40:00Z"
    }
  ]
}
```

---

### 4. WebSocket (Non prioritaire)

**Décision** : Polling REST toutes les 10-30s suffisant pour MVP.

Odds-API.io fournit WebSocket si besoin futur.

---

## Mapping Blocs → Endpoints

| Bloc | Endpoint(s) | Priorité |
|------|-------------|----------|
| Match Odds 1X2 | `GET /odds?market=ML` | P0 |
| Asian Handicap | `GET /odds?market=Asian Handicap` | P1 |
| Over/Under | `GET /odds?market=Totals` | P1 |
| BTTS | `GET /odds?market=Both Teams to Score` | P2 |
| Correct Score | `GET /odds?market=Correct Score` | P2 |
| Double Chance | `GET /odds?market=Double Chance` | P2 |
| Live Match Odds | `GET /events/live` + `GET /odds` | P0 |
| Live Score Widget | `GET /events/live` | P1 |
| Live Odds Ticker | `WS /ws/odds` | P3 |
| Value Bets | `GET /value-bets` | P1 |
| Arbitrage Finder | `GET /arbitrage-bets` | P1 |
| Odds Movement | `GET /odds/movements` | P2 |
| Upcoming Events | `GET /events?status=not_started` | P0 |
| Live Events List | `GET /events/live` | P1 |
| Event Search | `GET /events/search` | P2 |
| League Schedule | `GET /events?league=` + `GET /leagues` | P2 |
| Bookmaker Comparison | `GET /odds` | P0 |
| Odds Calculator | *Aucun (calcul local)* | P3 |

---

## Modèles DB

### Existants (à conserver)
- `RequestData` - tracking des demandes de génération
- `StaticFile` - fichiers JSON générés

### Optionnel (si besoin cache persistent)

**OddsHistoryCache** - Cache local de l'historique (si on veut éviter de re-fetcher) :
```python
class OddsHistoryCache(Base):
    id: UUID
    event_id: str
    bookmaker: str
    market: str
    movements_data: JSON  # Réponse Odds-API.io complète
    fetched_at: datetime
    expires_at: datetime  # fetched_at + 30 days
```

**Note** : Value bets et arbitrage ne nécessitent pas de stockage local - les données viennent en temps réel d'Odds-API.io.

---

## Services à Créer/Adapter

### 1. OddsMovementService
**Proxy** vers Odds-API.io `/odds/movements` avec :
- Cache Redis (TTL 5min)
- Stockage local optionnel pour historique > 30 jours
- Cleanup automatique

### 2. ValueBetService
**Proxy** vers Odds-API.io `/value-bets` avec :
- Cache Redis (TTL 2min)
- Filtrage par sport/league/minEV

### 3. ArbitrageService
**Proxy** vers Odds-API.io `/arbitrage-bets` avec :
- Cache Redis (TTL 2min)
- Filtrage par sport/minProfit

### 4. LiveEventsService
**Proxy** vers Odds-API.io `/events/live` avec :
- Cache Redis court (30s)
- Scores inclus dans la réponse
- Support filtrage par sport

---

## Modifications Fichiers Existants

### `app/api/routes.py`
- Ajouter routes `/events/live`, `/events/search`
- Ajouter route `/leagues`
- Améliorer `/events` avec filtres
- Ajouter `/odds/movements`
- Ajouter `/value-bets`, `/arbitrage-bets`

### `app/schemas/`
- Créer `events.py` avec EventResponse enrichi
- Créer `odds.py` avec formats multi-marchés
- Créer `analysis.py` pour value-bets/arbitrage

### `app/services/odds_client.py`
- Support multi-marchés (Asian Handicap, Totals, BTTS, etc.)
- Normalisation des réponses par marché

### `app/services/static_file.py`
- Support génération multi-marchés
- Hook pour OddsMovementService

### `app/worker.py`
- Nouveau job : `detect_value_bets`
- Nouveau job : `detect_arbitrage`
- Nouveau job : `record_odds_movement`

---

## Décisions Prises

1. **Source données live** : Odds-API.io fournit `/events/live` avec scores ✓
2. **WebSocket** : Polling REST suffisant (10-30s) pour MVP
3. **Stockage historique** : 30 jours de rétention
4. **Rate limits** : 5000 req/h standard, packages +10K/20K/30K dispo

---

## Implémentation Suggérée

### Phase 1 (P0)
- Améliorer `/events` avec filtres
- `/events/live`
- `/odds` multi-marchés (ML + Asian Handicap + Totals)
- `/leagues`

### Phase 2 (P1)
- Value bets + Arbitrage detection
- Odds movements history
- BTTS, Correct Score, Double Chance

### Phase 3 (P2-P3)
- Event search
- WebSocket (si nécessaire)
- Optimisations cache
