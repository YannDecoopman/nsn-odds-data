"""Tests for leagues routes."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_list_leagues_success(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /leagues returns leagues list."""
    leagues_data = [
        {"name": "Premier League", "slug": "premier-league", "sport": "football"},
        {"name": "La Liga", "slug": "la-liga", "sport": "football"},
    ]

    with patch("app.api.routes.leagues.odds_api_provider") as mock_provider:
        mock_provider.get_leagues = AsyncMock(return_value=leagues_data)

        response = await test_client.get("/leagues")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2
        assert data["data"][0]["name"] == "Premier League"
        assert data["data"][0]["slug"] == "premier-league"


@pytest.mark.asyncio
async def test_list_leagues_with_sport_filter(
    test_client, mock_cache_service, mock_metrics_service
):
    """Test GET /leagues with sport filter."""
    leagues_data = [{"name": "NBA", "slug": "nba", "sport": "basketball"}]

    with patch("app.api.routes.leagues.odds_api_provider") as mock_provider:
        mock_provider.get_leagues = AsyncMock(return_value=leagues_data)

        response = await test_client.get("/leagues", params={"sport": "basketball"})

        assert response.status_code == 200
        mock_provider.get_leagues.assert_called_once_with(sport="basketball")
        data = response.json()
        assert data["data"][0]["sport"] == "basketball"


@pytest.mark.asyncio
async def test_list_leagues_empty(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /leagues returns empty list when no leagues."""
    with patch("app.api.routes.leagues.odds_api_provider") as mock_provider:
        mock_provider.get_leagues = AsyncMock(return_value=[])

        response = await test_client.get("/leagues")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []


@pytest.mark.asyncio
async def test_list_leagues_with_missing_fields(
    test_client, mock_cache_service, mock_metrics_service
):
    """Test GET /leagues handles missing fields gracefully."""
    leagues_data = [
        {"name": "Test League"},  # Missing slug and sport
    ]

    with patch("app.api.routes.leagues.odds_api_provider") as mock_provider:
        mock_provider.get_leagues = AsyncMock(return_value=leagues_data)

        response = await test_client.get("/leagues")

        assert response.status_code == 200
        data = response.json()
        assert data["data"][0]["name"] == "Test League"
        assert data["data"][0]["slug"] == ""  # Default empty
