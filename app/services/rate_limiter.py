"""Rate limiting service using slowapi with Redis backend."""

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Get client IP, handling proxies via X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Configure limiter with Redis storage
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[settings.rate_limit_default],
    storage_uri=settings.redis_url,
    enabled=settings.rate_limit_enabled,
)
