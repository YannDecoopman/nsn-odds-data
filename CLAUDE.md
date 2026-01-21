# nsn-odds-data

Microservice for fetching and serving sports betting odds from Odds-API.io.

## Production

| | |
|---|---|
| **URL** | https://odds.jeanclaude.dev |
| **Docs** | https://odds.jeanclaude.dev/docs |
| **Repo** | github.com/YannDecoopman/nsn-odds-data |
| **Coolify** | NSN Odds API sur serveur-bot-slack |

## Deployment (Coolify)

### Création de l'app

1. **+ New** → **Public Repository**
2. Git repository: `https://github.com/YannDecoopman/nsn-odds-data`
3. Branch: `main`
4. Build Pack: **Docker Compose**
5. Server: `serveur-bot-slack`

### Environment Variables (obligatoires)

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/odds_data
REDIS_URL=redis://redis:6379/0
ODDS_API_KEY=<clé odds-api.io>
DEFAULT_BOOKMAKERS=Bet365
API_KEY_ENABLED=true
CORS_ORIGINS=https://odds.jeanclaude.dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=odds_data
```

### Configuration domaine

1. General → **Domains for app** : `https://odds.jeanclaude.dev`
2. **Save** → **Reload Compose File** → **Redeploy**

### Créer une API Key

Dans Coolify Terminal (container **db**) :

```bash
psql -U postgres -d odds_data -c "INSERT INTO api_keys (key, name, is_active, created_at) VALUES ('nsn_<token>', 'nom-site', true, NOW());"
```

Générer un token : `python3 -c "import secrets; print(f'nsn_{secrets.token_urlsafe(32)}')"`

## Docker Files

- `docker-compose.yaml` → **Production** (utilisé par Coolify)
- `docker-compose.dev.yml` → **Développement local**

## Endpoints

### P0 (Done)
- `GET /events` - List events with filters (sport, league, status, date_from, date_to)
- `GET /events/live` - Live events with scores
- `GET /odds?eventId=&market=` - Odds for event (1x2, asian_handicap, totals)
- `GET /leagues` - Available leagues

### P1 (Done)
- `GET /value-bets` - Value bets detection (multi-bookmaker aggregation)
- `GET /arbitrage-bets` - Arbitrage opportunities
- `GET /odds/movements` - Historical odds movements
- `GET /odds?market=btts` - Both Teams To Score
- `GET /odds?market=correct_score` - Correct Score
- `GET /odds?market=double_chance` - Double Chance

### P2-P3 (TODO)
- `GET /events/search` - Search events
- WebSocket for real-time odds

## Commandes

```bash
# Start
docker-compose up -d

# Rebuild after code changes
docker-compose build app && docker-compose up -d app

# Logs
docker-compose logs -f app
```

---

## Stack

- Python 3.12 + FastAPI
- PostgreSQL (async via asyncpg)
- Redis (cache + ARQ queue)
- Docker

## Commands

### Development

```bash
# Setup environment
cp .env.example .env
# Edit .env with your ODDS_API_KEY

# Start services
docker-compose up -d

# Run migrations
docker-compose exec app alembic upgrade head

# View logs
docker-compose logs -f app
```

### Local dev (without Docker)

```bash
# Install dependencies
uv sync

# Start postgres and redis (via docker)
docker-compose up -d db redis

# Run migrations
uv run alembic upgrade head

# Start app
uv run uvicorn app.main:app --reload

# Start worker (separate terminal)
uv run arq app.tasks.worker.WorkerSettings
```

### Testing

```bash
# Health check
curl http://localhost:8002/health

# Get sports
curl http://localhost:8002/sports

# Get events
curl "http://localhost:8002/events?sport=football"

# Get bookmakers
curl http://localhost:8002/bookmakers

# Generate odds file (use a valid event_id from /events)
curl -X POST http://localhost:8002/generate \
  -H "Content-Type: application/json" \
  -d '{"event_id": "EVENT_ID_HERE"}'

# Check file status
curl http://localhost:8002/files/{request_id}

# Get static file
curl http://localhost:8002/static/2026/01/odds-xxx.json
```

## Architecture

Pattern inspired by sportsdata-service (Symfony):

```
Request → RequestData (DB) → StaticFile (DB) → ARQ Task → JSON file
```

### Key files

- `app/main.py` - FastAPI routes
- `app/services/odds_client.py` - Odds-API.io HTTP client
- `app/services/static_file.py` - File generation with hash detection
- `app/providers/odds_api.py` - Provider pattern implementation
- `app/tasks/worker.py` - Background tasks + scheduler

### Data flow

1. POST /generate with event_id
2. Create/get RequestData record
3. Create/get StaticFile record with path
4. Queue ARQ task for async generation
5. Task fetches odds, computes hash
6. If hash changed, write JSON to static/
7. Scheduler refreshes active files every 5 minutes

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | - |
| `REDIS_URL` | Redis connection | redis://localhost:6379/0 |
| `ODDS_API_KEY` | API key from odds-api.io | - |
| `DEFAULT_BOOKMAKERS` | Comma-separated list | betano,sportingbet,betfair,bet365 |

## References

- **Odds-API.io documentation** : https://docs.odds-api.io/llms-full.txt
- **API Spec (endpoints à implémenter)** : `docs/API_SPEC.md`

## API Limitations (odds-api.io)

### Bookmaker Selection
- **Max 5 bookmakers** par plan (limitation API)
- Bookmakers actuellement sélectionnés : `Betano, Pixbet, Betnacional, KTO, Estrela Bet`
- Pour changer : `PUT /bookmakers/selected/clear?apiKey=YOUR_API_KEY`

### Disponibilité des marchés par bookmaker

| Marché | Bookmakers BR | Bookmakers EU/Asia |
|--------|---------------|-------------------|
| 1X2 | ✅ Disponible | ✅ Disponible |
| Totals (O/U) | ✅ Disponible | ✅ Disponible |
| BTTS | ❌ Non disponible | ✅ Bet365, Pinnacle |
| Asian Handicap | ❌ Non disponible | ✅ Bet365, Pinnacle, Sbobet |
| Correct Score | ⚠️ Partiel | ✅ La plupart |
| Double Chance | ✅ Disponible | ✅ Disponible |

**Important** : Les bookmakers brésiliens (Betano, Pixbet, Betnacional, KTO, Estrela Bet) ne proposent PAS les marchés **Asian Handicap** et **BTTS**. Pour ces marchés, il faut des bookmakers européens/asiatiques (Bet365, Pinnacle, Sbobet).

### Erreurs courantes

```
HTTP 403: Access denied. You're allowed max 5 bookmakers.
```
→ Upgrade plan ou changer les bookmakers sélectionnés

```
No odds data for event {id}
```
→ Le marché demandé n'est pas disponible chez les bookmakers sélectionnés

## Notes

- All sports supported via Odds-API.io
- Markets: 1x2, asian_handicap, totals, btts, correct_score, double_chance
- Brazilian bookmakers: betano, sportingbet, betfair, bet365
- WordPress plugin: Phase 2 (see nsn-soccer-data for reference)
