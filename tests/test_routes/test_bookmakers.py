"""Tests for /bookmakers endpoints."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_list_bookmakers_success(test_client, mock_cache_service, mock_metrics_service):
    """Test listing bookmakers returns data."""
    bookmakers_data = [
        {"key": "bet365", "name": "Bet365", "region": "uk", "isActive": True},
        {"key": "betano", "name": "Betano", "region": "br", "isActive": True},
    ]

    with patch("app.api.routes.bookmakers.odds_api_provider") as mock:
        mock.get_bookmakers = AsyncMock(return_value=bookmakers_data)
        response = await test_client.get("/bookmakers")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["key"] == "bet365"
    assert data[0]["name"] == "Bet365"
    assert data[0]["region"] == "uk"


@pytest.mark.asyncio
async def test_list_bookmakers_empty(test_client, mock_cache_service, mock_metrics_service):
    """Test listing bookmakers with no data."""
    with patch("app.api.routes.bookmakers.odds_api_provider") as mock:
        mock.get_bookmakers = AsyncMock(return_value=[])
        response = await test_client.get("/bookmakers")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_bookmakers_with_missing_fields(test_client, mock_cache_service, mock_metrics_service):
    """Test bookmakers with missing optional fields."""
    bookmakers_data = [
        {"key": "bet365", "name": "Bet365"},  # No region or isActive
    ]

    with patch("app.api.routes.bookmakers.odds_api_provider") as mock:
        mock.get_bookmakers = AsyncMock(return_value=bookmakers_data)
        response = await test_client.get("/bookmakers")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["region"] is None  # Default
    assert data[0]["is_active"] is True  # Default
