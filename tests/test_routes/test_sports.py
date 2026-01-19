"""Tests for /sports endpoints."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_list_sports_success(test_client, mock_cache_service, mock_metrics_service):
    """Test listing sports returns data."""
    sports_data = [
        {"name": "Football", "slug": "football", "active": True},
        {"name": "Basketball", "slug": "basketball", "active": True},
    ]

    with patch("app.api.routes.sports.odds_api_provider") as mock:
        mock.get_sports = AsyncMock(return_value=sports_data)
        response = await test_client.get("/sports")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["key"] == "football"
    assert data[0]["title"] == "Football"
    assert data[0]["active"] is True


@pytest.mark.asyncio
async def test_list_sports_empty(test_client, mock_cache_service, mock_metrics_service):
    """Test listing sports with no data."""
    with patch("app.api.routes.sports.odds_api_provider") as mock:
        mock.get_sports = AsyncMock(return_value=[])
        response = await test_client.get("/sports")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_sports_with_missing_fields(test_client, mock_cache_service, mock_metrics_service):
    """Test sports with missing optional fields."""
    sports_data = [
        {"name": "Football", "slug": "football"},  # No active field
    ]

    with patch("app.api.routes.sports.odds_api_provider") as mock:
        mock.get_sports = AsyncMock(return_value=sports_data)
        response = await test_client.get("/sports")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["active"] is True  # Default value
