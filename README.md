# nsn-odds-data

Microservice for fetching sports betting odds and generating static JSON files.

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
curl http://localhost:8000/health
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/sports` | List available sports |
| GET | `/events?sport=football` | List events |
| GET | `/bookmakers` | List configured bookmakers |
| POST | `/generate` | Request odds file generation |
| GET | `/files/{id}` | Get file generation status |
| GET | `/static/{path}` | Serve generated JSON |

## License

Proprietary - North Star Network
