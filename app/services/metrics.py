"""Metrics service for tracking API usage and performance."""

import logging
import time
from datetime import datetime
from typing import Any

from app.services.cache import cache_service

logger = logging.getLogger(__name__)

# Redis keys for metrics
METRICS_PREFIX = "metrics:"
KEY_REQUEST_COUNT = f"{METRICS_PREFIX}requests"
KEY_ERROR_COUNT = f"{METRICS_PREFIX}errors"
KEY_LATENCY_SUM = f"{METRICS_PREFIX}latency_sum"
KEY_LATENCY_COUNT = f"{METRICS_PREFIX}latency_count"
KEY_CACHE_HITS = f"{METRICS_PREFIX}cache_hits"
KEY_CACHE_MISSES = f"{METRICS_PREFIX}cache_misses"
KEY_API_CALLS = f"{METRICS_PREFIX}api_calls"
KEY_LAST_RESET = f"{METRICS_PREFIX}last_reset"


class MetricsService:
    """Service for collecting and reporting metrics."""

    async def increment(self, key: str, amount: int = 1) -> None:
        """Increment a counter in Redis."""
        try:
            redis = await cache_service._get_redis()
            await redis.incrby(key, amount)
        except Exception as e:
            logger.debug(f"Failed to increment metric {key}: {e}")

    async def get_value(self, key: str) -> int:
        """Get a counter value from Redis."""
        try:
            redis = await cache_service._get_redis()
            value = await redis.get(key)
            return int(value) if value else 0
        except Exception:
            return 0

    async def track_request(self) -> None:
        """Track an API request."""
        await self.increment(KEY_REQUEST_COUNT)

    async def track_error(self) -> None:
        """Track an API error."""
        await self.increment(KEY_ERROR_COUNT)

    async def track_latency(self, latency_ms: float) -> None:
        """Track request latency."""
        await self.increment(KEY_LATENCY_SUM, int(latency_ms))
        await self.increment(KEY_LATENCY_COUNT)

    async def track_cache_hit(self) -> None:
        """Track a cache hit."""
        await self.increment(KEY_CACHE_HITS)

    async def track_cache_miss(self) -> None:
        """Track a cache miss."""
        await self.increment(KEY_CACHE_MISSES)

    async def track_api_call(self) -> None:
        """Track an external API call."""
        await self.increment(KEY_API_CALLS)

    async def get_metrics(self) -> dict[str, Any]:
        """Get all metrics."""
        requests = await self.get_value(KEY_REQUEST_COUNT)
        errors = await self.get_value(KEY_ERROR_COUNT)
        latency_sum = await self.get_value(KEY_LATENCY_SUM)
        latency_count = await self.get_value(KEY_LATENCY_COUNT)
        cache_hits = await self.get_value(KEY_CACHE_HITS)
        cache_misses = await self.get_value(KEY_CACHE_MISSES)
        api_calls = await self.get_value(KEY_API_CALLS)

        # Calculate averages
        avg_latency = latency_sum / latency_count if latency_count > 0 else 0
        cache_total = cache_hits + cache_misses
        cache_hit_rate = (cache_hits / cache_total * 100) if cache_total > 0 else 0
        error_rate = (errors / requests * 100) if requests > 0 else 0

        # Get last reset time
        try:
            redis = await cache_service._get_redis()
            last_reset = await redis.get(KEY_LAST_RESET)
            last_reset_str = last_reset.decode() if last_reset else None
        except Exception:
            last_reset_str = None

        return {
            "requests": {
                "total": requests,
                "errors": errors,
                "error_rate_percent": round(error_rate, 2),
            },
            "latency": {
                "avg_ms": round(avg_latency, 2),
                "samples": latency_count,
            },
            "cache": {
                "hits": cache_hits,
                "misses": cache_misses,
                "hit_rate_percent": round(cache_hit_rate, 2),
            },
            "external_api": {
                "calls": api_calls,
            },
            "last_reset": last_reset_str,
            "collected_at": datetime.now().isoformat(),
        }

    async def reset(self) -> None:
        """Reset all metrics."""
        try:
            redis = await cache_service._get_redis()
            keys = [
                KEY_REQUEST_COUNT,
                KEY_ERROR_COUNT,
                KEY_LATENCY_SUM,
                KEY_LATENCY_COUNT,
                KEY_CACHE_HITS,
                KEY_CACHE_MISSES,
                KEY_API_CALLS,
            ]
            for key in keys:
                await redis.delete(key)
            await redis.set(KEY_LAST_RESET, datetime.now().isoformat())
        except Exception as e:
            logger.error(f"Failed to reset metrics: {e}")


metrics_service = MetricsService()
