# nsn-odds-data

Microservice for fetching sports betting odds from Odds-API.io.

## Quick Start

```bash
# Copy environment file
cp .env.example .env

# Add your Odds-API.io key to .env
# ODDS_API_KEY=your_key_here

# Start with Docker
docker-compose up -d

# Run migrations
docker-compose exec app alembic upgrade head

# Test
curl http://localhost:8002/health
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/sports` | List available sports |
| GET | `/bookmakers` | List configured bookmakers |
| GET | `/events` | List events with filters and pagination |
| GET | `/events/live` | Live events with scores (30s cache) |
| GET | `/leagues` | List leagues by sport |
| GET | `/odds` | Get odds (1x2, asian_handicap, totals) |
| POST | `/generate` | Request odds file generation |
| GET | `/files/{id}` | Get file generation status |
| GET | `/static/{path}` | Serve generated JSON |

See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) for full documentation.

## Stack

- Python 3.12 + FastAPI
- PostgreSQL (asyncpg)
- Redis (cache + ARQ queue)
- Docker

## License

Proprietary - North Star Network
