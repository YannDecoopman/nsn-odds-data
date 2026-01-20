"""Tests for value bets routes."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.events import LeagueInfo, SportInfo
from app.schemas.value_bets import (
    ConsensusOdds,
    ValueBet,
    ValueBetEvent,
    ValueBetOdds,
    ValueBetsResponse,
)


@pytest.mark.asyncio
async def test_list_value_bets_success(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /value-bets returns value bets."""
    value_bet = ValueBet(
        id="vb_123",
        eventId="evt_123",
        bookmaker="Bet365",
        market="ML",
        betSide="home",
        expectedValue=5.5,
        expectedValueUpdatedAt=datetime(2026, 1, 18, 10, 0, 0),
        bookmakerOdds=ValueBetOdds(home=2.10, draw=3.40, away=3.80, homeDirectLink="https://bet365.com"),
        consensusOdds=ConsensusOdds(home=1.95, draw=3.50, away=4.00),
        event=ValueBetEvent(
            home="Team A",
            away="Team B",
            date=datetime(2026, 1, 20, 15, 0, 0),
            sport=SportInfo(name="Football", slug="football"),
            league=LeagueInfo(name="Premier League", slug="premier-league"),
        ),
    )
    response_data = ValueBetsResponse(data=[value_bet])

    with patch("app.api.routes.value_bets.odds_api_provider") as mock_provider:
        mock_provider.get_value_bets = AsyncMock(return_value=response_data)

        response = await test_client.get("/value-bets", params={"region": "uk"})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["expectedValue"] == 5.5
        assert data["data"][0]["bookmaker"] == "Bet365"


@pytest.mark.asyncio
async def test_list_value_bets_with_sport_filter(
    test_client, mock_cache_service, mock_metrics_service
):
    """Test GET /value-bets with sport filter."""
    with patch("app.api.routes.value_bets.odds_api_provider") as mock_provider:
        mock_provider.get_value_bets = AsyncMock(return_value=ValueBetsResponse(data=[]))

        response = await test_client.get("/value-bets", params={"region": "uk", "sport": "basketball"})

        assert response.status_code == 200
        call_kwargs = mock_provider.get_value_bets.call_args[1]
        assert call_kwargs["sport"] == "basketball"


@pytest.mark.asyncio
async def test_list_value_bets_with_min_ev(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /value-bets with minEV filter."""
    with patch("app.api.routes.value_bets.odds_api_provider") as mock_provider:
        mock_provider.get_value_bets = AsyncMock(return_value=ValueBetsResponse(data=[]))

        response = await test_client.get("/value-bets", params={"region": "uk", "minEV": 5.0})

        assert response.status_code == 200
        call_kwargs = mock_provider.get_value_bets.call_args[1]
        assert call_kwargs["min_ev"] == 5.0


@pytest.mark.asyncio
async def test_list_value_bets_with_league_filter(
    test_client, mock_cache_service, mock_metrics_service
):
    """Test GET /value-bets with league filter."""
    with patch("app.api.routes.value_bets.odds_api_provider") as mock_provider:
        mock_provider.get_value_bets = AsyncMock(return_value=ValueBetsResponse(data=[]))

        response = await test_client.get("/value-bets", params={"region": "uk", "league": "premier-league"})

        assert response.status_code == 200
        call_kwargs = mock_provider.get_value_bets.call_args[1]
        assert call_kwargs["league"] == "premier-league"


@pytest.mark.asyncio
async def test_list_value_bets_with_limit(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /value-bets with limit parameter."""
    with patch("app.api.routes.value_bets.odds_api_provider") as mock_provider:
        mock_provider.get_value_bets = AsyncMock(return_value=ValueBetsResponse(data=[]))

        response = await test_client.get("/value-bets", params={"region": "uk", "limit": 25})

        assert response.status_code == 200
        call_kwargs = mock_provider.get_value_bets.call_args[1]
        assert call_kwargs["limit"] == 25


@pytest.mark.asyncio
async def test_list_value_bets_empty(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /value-bets returns empty list."""
    with patch("app.api.routes.value_bets.odds_api_provider") as mock_provider:
        mock_provider.get_value_bets = AsyncMock(return_value=ValueBetsResponse(data=[]))

        response = await test_client.get("/value-bets", params={"region": "uk"})

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []


@pytest.mark.asyncio
async def test_list_value_bets_limit_validation(
    test_client, mock_cache_service, mock_metrics_service
):
    """Test GET /value-bets rejects limit > 50."""
    response = await test_client.get("/value-bets", params={"region": "uk", "limit": 100})
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_value_bets_missing_region(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /value-bets without region returns 422."""
    response = await test_client.get("/value-bets")
    assert response.status_code == 422  # Validation error - region is required


@pytest.mark.asyncio
async def test_list_value_bets_region_bookmakers(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /value-bets passes correct bookmakers for region."""
    with patch("app.api.routes.value_bets.odds_api_provider") as mock_provider:
        mock_provider.get_value_bets = AsyncMock(return_value=ValueBetsResponse(data=[]))

        response = await test_client.get("/value-bets", params={"region": "br"})

        assert response.status_code == 200
        call_kwargs = mock_provider.get_value_bets.call_args[1]
        # Should pass Brazilian bookmakers
        assert "betano" in call_kwargs["bookmakers"]
        assert "pixbet" in call_kwargs["bookmakers"]
