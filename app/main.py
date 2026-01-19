import logging
import time
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import (
    arbitrage,
    bookmakers,
    events,
    leagues,
    odds,
    participants,
    sports,
    static_files,
    value_bets,
)
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
from app.services.cache import cache_service
from app.services.metrics import metrics_service
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# API Key authentication middleware
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Validate API key if enabled."""
    # Skip auth for health/docs endpoints
    if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)

    # Skip if API key auth is disabled
    if not settings.api_key_enabled or not settings.api_key:
        return await call_next(request)

    # Check API key
    api_key = request.headers.get("X-API-Key")
    if api_key != settings.api_key:
        return JSONResponse(
            status_code=401,
            content={"error": "UNAUTHORIZED", "message": "Invalid or missing API key"},
        )

    return await call_next(request)


# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request metrics."""
    # Skip metrics for health/metrics endpoints
    if request.url.path in ("/health", "/metrics"):
        return await call_next(request)

    start_time = time.time()
    await metrics_service.track_request()

    response = await call_next(request)

    # Track latency
    latency_ms = (time.time() - start_time) * 1000
    await metrics_service.track_latency(latency_ms)

    # Track errors
    if response.status_code >= 400:
        await metrics_service.track_error()

    return response


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
app.include_router(sports.router, prefix="/sports", tags=["sports"])
app.include_router(bookmakers.router, prefix="/bookmakers", tags=["bookmakers"])
app.include_router(participants.router, prefix="/participants", tags=["participants"])
app.include_router(static_files.router, tags=["static"])
app.include_router(value_bets.router, prefix="/value-bets", tags=["analysis"])
app.include_router(arbitrage.router, prefix="/arbitrage-bets", tags=["analysis"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "nsn-odds-data"}


@app.get("/metrics")
async def get_metrics():
    """Get API metrics (requests, latency, cache stats)."""
    return await metrics_service.get_metrics()


@app.post("/metrics/reset")
async def reset_metrics():
    """Reset all metrics counters."""
    await metrics_service.reset()
    return {"status": "reset"}
