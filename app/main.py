import logging
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI

from app.api.routes import events, leagues, odds, static_files
from app.config import settings
from app.providers.odds_api import odds_api_provider
from app.schemas import BookmakerResponse, SportResponse
from app.services.cache import cache_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting nsn-odds-data service")
    try:
        app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}. Background tasks disabled.")
        app.state.arq_pool = None
    yield
    # Shutdown
    await cache_service.close()
    if app.state.arq_pool:
        await app.state.arq_pool.close()
    logger.info("Shutting down nsn-odds-data service")


app = FastAPI(
    title="nsn-odds-data",
    description="Microservice for sports betting odds",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(odds.router, prefix="/odds", tags=["odds"])
app.include_router(leagues.router, prefix="/leagues", tags=["leagues"])
app.include_router(static_files.router, tags=["static"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "nsn-odds-data"}


@app.get("/sports", response_model=list[SportResponse])
async def get_sports():
    """Get available sports from Odds-API.io."""
    sports = await odds_api_provider.get_sports()
    return [
        SportResponse(
            key=s.get("slug", s.get("key", "")),
            title=s.get("name", s.get("title", "")),
            active=s.get("active", True),
        )
        for s in sports
    ]


@app.get("/bookmakers", response_model=list[BookmakerResponse])
async def get_bookmakers():
    """Get configured bookmakers."""
    return [
        BookmakerResponse(key=bm, name=bm.title(), region="br")
        for bm in settings.bookmakers_list
    ]
