"""Tests for cache service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.cache import CacheService


@pytest.fixture
def cache_service():
    """Create CacheService instance."""
    return CacheService()


@pytest.mark.asyncio
async def test_get_cache_hit(cache_service):
    """Test get returns cached data."""
    cached_data = {"key": "value"}

    with (
        patch("app.services.cache.redis") as mock_redis_module,
        patch("app.services.cache.settings") as mock_settings,
    ):
        mock_settings.redis_url = "redis://localhost:6379/0"

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        # Mock metrics
        with patch("app.services.metrics.metrics_service") as mock_metrics:
            mock_metrics.track_cache_hit = AsyncMock()

            result = await cache_service.get("test_key")

            assert result == cached_data
            mock_metrics.track_cache_hit.assert_called_once()


@pytest.mark.asyncio
async def test_get_cache_miss(cache_service):
    """Test get returns None on cache miss."""
    with (
        patch("app.services.cache.redis") as mock_redis_module,
        patch("app.services.cache.settings") as mock_settings,
    ):
        mock_settings.redis_url = "redis://localhost:6379/0"

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch("app.services.metrics.metrics_service") as mock_metrics:
            mock_metrics.track_cache_miss = AsyncMock()

            result = await cache_service.get("missing_key")

            assert result is None
            mock_metrics.track_cache_miss.assert_called_once()


@pytest.mark.asyncio
async def test_get_no_metrics(cache_service):
    """Test get with track_metrics=False."""
    cached_data = {"key": "value"}

    with (
        patch("app.services.cache.redis") as mock_redis_module,
        patch("app.services.cache.settings") as mock_settings,
    ):
        mock_settings.redis_url = "redis://localhost:6379/0"

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch("app.services.metrics.metrics_service") as mock_metrics:
            mock_metrics.track_cache_hit = AsyncMock()

            result = await cache_service.get("test_key", track_metrics=False)

            assert result == cached_data
            mock_metrics.track_cache_hit.assert_not_called()


@pytest.mark.asyncio
async def test_set_with_ttl(cache_service):
    """Test set stores data with TTL."""
    data = {"foo": "bar"}

    with (
        patch("app.services.cache.redis") as mock_redis_module,
        patch("app.services.cache.settings") as mock_settings,
    ):
        mock_settings.redis_url = "redis://localhost:6379/0"

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        await cache_service.set("test_key", data, ttl=300)

        mock_redis.set.assert_called_once_with("test_key", json.dumps(data), ex=300)


@pytest.mark.asyncio
async def test_set_without_ttl(cache_service):
    """Test set stores data without TTL."""
    data = {"foo": "bar"}

    with (
        patch("app.services.cache.redis") as mock_redis_module,
        patch("app.services.cache.settings") as mock_settings,
    ):
        mock_settings.redis_url = "redis://localhost:6379/0"

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        await cache_service.set("test_key", data)

        mock_redis.set.assert_called_once_with("test_key", json.dumps(data), ex=None)


@pytest.mark.asyncio
async def test_delete(cache_service):
    """Test delete removes key."""
    with (
        patch("app.services.cache.redis") as mock_redis_module,
        patch("app.services.cache.settings") as mock_settings,
    ):
        mock_settings.redis_url = "redis://localhost:6379/0"

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        await cache_service.delete("test_key")

        mock_redis.delete.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_close(cache_service):
    """Test close closes Redis connection."""
    with (
        patch("app.services.cache.redis") as mock_redis_module,
        patch("app.services.cache.settings") as mock_settings,
    ):
        mock_settings.redis_url = "redis://localhost:6379/0"

        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        # Initialize connection
        await cache_service.get_client()

        await cache_service.close()

        mock_redis.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_client_reuses_connection(cache_service):
    """Test get_client reuses existing connection."""
    with (
        patch("app.services.cache.redis") as mock_redis_module,
        patch("app.services.cache.settings") as mock_settings,
    ):
        mock_settings.redis_url = "redis://localhost:6379/0"

        mock_redis = AsyncMock()
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        # First call
        client1 = await cache_service.get_client()

        # Second call
        client2 = await cache_service.get_client()

        # Should be same instance
        assert client1 is client2
        # from_url should only be called once
        assert mock_redis_module.from_url.call_count == 1


@pytest.mark.asyncio
async def test_get_complex_data(cache_service):
    """Test get handles complex nested data."""
    cached_data = {
        "events": [
            {"id": "1", "home": "Team A", "away": "Team B"},
            {"id": "2", "home": "Team C", "away": "Team D"},
        ],
        "pagination": {"total": 2, "limit": 10},
    }

    with (
        patch("app.services.cache.redis") as mock_redis_module,
        patch("app.services.cache.settings") as mock_settings,
    ):
        mock_settings.redis_url = "redis://localhost:6379/0"

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))
        mock_redis_module.from_url = MagicMock(return_value=mock_redis)

        with patch("app.services.metrics.metrics_service") as mock_metrics:
            mock_metrics.track_cache_hit = AsyncMock()

            result = await cache_service.get("events_cache")

            assert result == cached_data
            assert len(result["events"]) == 2
