import json
from typing import Any

import redis.asyncio as redis

from app.config import settings

# Cache keys
CACHE_KEY_UPCOMING = "upcoming_events"


class CacheService:
    """Redis cache wrapper."""

    def __init__(self):
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        """Get raw Redis client (for metrics)."""
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def get_client(self) -> redis.Redis:
        return await self._get_redis()

    async def get(self, key: str, track_metrics: bool = True) -> Any | None:
        client = await self.get_client()
        value = await client.get(key)

        # Track cache hit/miss (lazy import to avoid circular deps)
        if track_metrics:
            from app.services.metrics import metrics_service
            if value:
                await metrics_service.track_cache_hit()
            else:
                await metrics_service.track_cache_miss()

        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        client = await self.get_client()
        await client.set(key, json.dumps(value), ex=ttl)

    async def delete(self, key: str) -> None:
        client = await self.get_client()
        await client.delete(key)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()


cache_service = CacheService()
