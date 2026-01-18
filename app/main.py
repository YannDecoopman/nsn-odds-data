import logging
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import arbitrage, events, leagues, odds, static_files, value_bets
from app.config import settings
from app.exceptions import (
    CacheError,
    DatabaseError,
    EventNotFoundError,
    OddsAPIError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
    ValidationError,
)
from app.providers.odds_api import odds_api_provider
from app.schemas import BookmakerResponse, SportResponse
from app.services.cache import cache_service
from app.services.rate_limiter import limiter

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

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Exception handlers
@app.exception_handler(RateLimitError)
async def rate_limit_handler(request: Request, exc: RateLimitError):
    logger.warning(f"Rate limit: {exc.message} - {exc.details}")
    return JSONResponse(status_code=429, content=exc.to_dict())


@app.exception_handler(ProviderTimeoutError)
async def timeout_handler(request: Request, exc: ProviderTimeoutError):
    logger.error(f"Provider timeout: {exc.message} - {exc.details}")
    return JSONResponse(status_code=504, content=exc.to_dict())


@app.exception_handler(EventNotFoundError)
async def event_not_found_handler(request: Request, exc: EventNotFoundError):
    logger.info(f"Event not found: {exc.event_id}")
    return JSONResponse(status_code=404, content=exc.to_dict())


@app.exception_handler(ProviderError)
async def provider_error_handler(request: Request, exc: ProviderError):
    logger.error(f"Provider error: {exc.message} - {exc.details}")
    status = exc.status_code if exc.status_code and 400 <= exc.status_code < 600 else 502
    return JSONResponse(status_code=status, content=exc.to_dict())


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    logger.info(f"Validation error: {exc.message} - {exc.details}")
    return JSONResponse(status_code=400, content=exc.to_dict())


@app.exception_handler(CacheError)
async def cache_error_handler(request: Request, exc: CacheError):
    logger.error(f"Cache error: {exc.message} - {exc.details}")
    return JSONResponse(status_code=503, content=exc.to_dict())


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    logger.error(f"Database error: {exc.message} - {exc.details}")
    return JSONResponse(status_code=503, content=exc.to_dict())


@app.exception_handler(OddsAPIError)
async def odds_api_error_handler(request: Request, exc: OddsAPIError):
    logger.error(f"OddsAPI error: {exc.message} - {exc.details}")
    return JSONResponse(status_code=500, content=exc.to_dict())


# Include routers
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(odds.router, prefix="/odds", tags=["odds"])
app.include_router(leagues.router, prefix="/leagues", tags=["leagues"])
app.include_router(static_files.router, tags=["static"])
app.include_router(value_bets.router, prefix="/value-bets", tags=["analysis"])
app.include_router(arbitrage.router, prefix="/arbitrage-bets", tags=["analysis"])


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
