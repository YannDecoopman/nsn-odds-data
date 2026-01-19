"""Tests for /participants endpoints."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_list_participants_success(test_client, mock_cache_service, mock_metrics_service):
    """Test listing participants returns data."""
    participants_data = [
        {"id": "p1", "name": "Manchester United", "slug": "manchester-united", "sport": "football", "country": "England"},
        {"id": "p2", "name": "Real Madrid", "slug": "real-madrid", "sport": "football", "country": "Spain"},
    ]

    with patch("app.api.routes.participants.odds_api_provider") as mock:
        mock.get_participants = AsyncMock(return_value=participants_data)
        response = await test_client.get("/participants?sport=football")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["data"]) == 2
    assert data["data"][0]["name"] == "Manchester United"


@pytest.mark.asyncio
async def test_list_participants_with_search(test_client, mock_cache_service, mock_metrics_service):
    """Test searching participants by name."""
    participants_data = [
        {"id": "p1", "name": "Manchester United", "slug": "manchester-united", "sport": "football"},
    ]

    with patch("app.api.routes.participants.odds_api_provider") as mock:
        mock.get_participants = AsyncMock(return_value=participants_data)
        response = await test_client.get("/participants?sport=football&search=manchester")

    assert response.status_code == 200
    mock.get_participants.assert_called_once_with(sport="football", search="manchester")


@pytest.mark.asyncio
async def test_list_participants_missing_sport(test_client, mock_cache_service, mock_metrics_service):
    """Test error when sport is missing."""
    response = await test_client.get("/participants")

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_participants_empty(test_client, mock_cache_service, mock_metrics_service):
    """Test listing participants with no data."""
    with patch("app.api.routes.participants.odds_api_provider") as mock:
        mock.get_participants = AsyncMock(return_value=[])
        response = await test_client.get("/participants?sport=football")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["data"] == []


@pytest.mark.asyncio
async def test_list_participants_pagination(test_client, mock_cache_service, mock_metrics_service):
    """Test pagination for participants."""
    participants_data = [{"id": f"p{i}", "name": f"Team {i}", "sport": "football"} for i in range(20)]

    with patch("app.api.routes.participants.odds_api_provider") as mock:
        mock.get_participants = AsyncMock(return_value=participants_data)
        response = await test_client.get("/participants?sport=football&limit=5&offset=10")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 20
    assert len(data["data"]) == 5
    assert data["data"][0]["name"] == "Team 10"


@pytest.mark.asyncio
async def test_get_participant_by_id_success(test_client, mock_cache_service, mock_metrics_service):
    """Test getting a single participant by ID."""
    participant_data = {
        "id": "p1",
        "name": "Manchester United",
        "slug": "manchester-united",
        "sport": "football",
        "country": "England",
        "logo": "https://example.com/logo.png",
    }

    with patch("app.api.routes.participants.odds_api_provider") as mock:
        mock.get_participant = AsyncMock(return_value=participant_data)
        response = await test_client.get("/participants/p1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "p1"
    assert data["name"] == "Manchester United"


@pytest.mark.asyncio
async def test_get_participant_by_id_not_found(test_client, mock_cache_service, mock_metrics_service):
    """Test 404 when participant not found."""
    with patch("app.api.routes.participants.odds_api_provider") as mock:
        mock.get_participant = AsyncMock(return_value=None)
        response = await test_client.get("/participants/invalid_id")

    assert response.status_code == 404
