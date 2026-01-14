# nsn-odds-data

Microservice for fetching and serving sports betting odds from Odds-API.io.

## TODO - Prochaine session

**Objectif** : Implémenter les endpoints définis dans `docs/API_SPEC.md` pour supporter les 18 blocs du plugin WordPress.

### Phase 1 (P0) - À faire maintenant
1. `GET /events` - Ajouter filtres (sport, league, status, date_from, date_to, pagination)
2. `GET /events/live` - Nouveau endpoint (proxy Odds-API.io avec cache 30s)
3. `GET /odds` - Support multi-marchés (Asian Handicap, Totals en plus de ML)
4. `GET /leagues` - Nouveau endpoint

### Fichiers à modifier
- `app/api/routes.py` - Ajouter les routes
- `app/schemas/` - Créer schemas pour nouveaux endpoints
- `app/services/odds_client.py` - Support multi-marchés

### Commandes de démarrage
```bash
cd /Users/yann-mbp/Documents/Projets/wodds/nsn-odds-data
docker-compose up -d
uv run uvicorn app.main:app --reload --port 8002
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

## Notes

- MVP: Football 1X2 only
- Brazilian bookmakers: betano, sportingbet, betfair, bet365
- WordPress plugin: Phase 2 (see nsn-soccer-data for reference)
