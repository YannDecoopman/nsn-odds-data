"""Tests for arbitrage routes."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.arbitrage import (
    ArbitrageBet,
    ArbitrageEvent,
    ArbitrageLeg,
    ArbitrageResponse,
    OptimalStake,
)
from app.schemas.events import LeagueInfo, SportInfo


@pytest.mark.asyncio
async def test_list_arbitrage_bets_success(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /arbitrage-bets returns arbitrage opportunities."""
    arb_bet = ArbitrageBet(
        id="arb_456",
        eventId="evt_456",
        market="ML",
        profitMargin=2.5,
        impliedProbability=97.5,
        totalStake=100.0,
        legs=[
            ArbitrageLeg(side="home", bookmaker="Bet365", odds=2.10, directLink="https://bet365.com"),
            ArbitrageLeg(side="away", bookmaker="Betfair", odds=2.20, directLink="https://betfair.com"),
        ],
        optimalStakes=[
            OptimalStake(side="home", bookmaker="Bet365", stake=51.2, potentialReturn=107.52),
            OptimalStake(side="away", bookmaker="Betfair", stake=48.8, potentialReturn=107.36),
        ],
        event=ArbitrageEvent(
            home="Team E",
            away="Team F",
            date=datetime(2026, 1, 21, 18, 0, 0),
            sport=SportInfo(name="Football", slug="football"),
            league=LeagueInfo(name="Serie A", slug="serie-a"),
        ),
        detectedAt=datetime(2026, 1, 18, 12, 0, 0),
    )
    response_data = ArbitrageResponse(data=[arb_bet])

    with patch("app.api.routes.arbitrage.odds_api_provider") as mock_provider:
        mock_provider.get_arbitrage_bets = AsyncMock(return_value=response_data)

        response = await test_client.get("/arbitrage-bets", params={"region": "uk"})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["profitMargin"] == 2.5
        assert len(data["data"][0]["legs"]) == 2


@pytest.mark.asyncio
async def test_list_arbitrage_bets_with_sport_filter(
    test_client, mock_cache_service, mock_metrics_service
):
    """Test GET /arbitrage-bets with sport filter."""
    with patch("app.api.routes.arbitrage.odds_api_provider") as mock_provider:
        mock_provider.get_arbitrage_bets = AsyncMock(return_value=ArbitrageResponse(data=[]))

        response = await test_client.get("/arbitrage-bets", params={"region": "uk", "sport": "tennis"})

        assert response.status_code == 200
        call_kwargs = mock_provider.get_arbitrage_bets.call_args[1]
        assert call_kwargs["sport"] == "tennis"


@pytest.mark.asyncio
async def test_list_arbitrage_bets_with_min_profit(
    test_client, mock_cache_service, mock_metrics_service
):
    """Test GET /arbitrage-bets with minProfit filter."""
    with patch("app.api.routes.arbitrage.odds_api_provider") as mock_provider:
        mock_provider.get_arbitrage_bets = AsyncMock(return_value=ArbitrageResponse(data=[]))

        response = await test_client.get("/arbitrage-bets", params={"region": "uk", "minProfit": 3.0})

        assert response.status_code == 200
        call_kwargs = mock_provider.get_arbitrage_bets.call_args[1]
        assert call_kwargs["min_profit"] == 3.0


@pytest.mark.asyncio
async def test_list_arbitrage_bets_with_limit(
    test_client, mock_cache_service, mock_metrics_service
):
    """Test GET /arbitrage-bets with limit parameter."""
    with patch("app.api.routes.arbitrage.odds_api_provider") as mock_provider:
        mock_provider.get_arbitrage_bets = AsyncMock(return_value=ArbitrageResponse(data=[]))

        response = await test_client.get("/arbitrage-bets", params={"region": "uk", "limit": 10})

        assert response.status_code == 200
        call_kwargs = mock_provider.get_arbitrage_bets.call_args[1]
        assert call_kwargs["limit"] == 10


@pytest.mark.asyncio
async def test_list_arbitrage_bets_empty(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /arbitrage-bets returns empty list."""
    with patch("app.api.routes.arbitrage.odds_api_provider") as mock_provider:
        mock_provider.get_arbitrage_bets = AsyncMock(return_value=ArbitrageResponse(data=[]))

        response = await test_client.get("/arbitrage-bets", params={"region": "uk"})

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []


@pytest.mark.asyncio
async def test_list_arbitrage_bets_limit_validation(
    test_client, mock_cache_service, mock_metrics_service
):
    """Test GET /arbitrage-bets rejects limit > 50."""
    response = await test_client.get("/arbitrage-bets", params={"region": "uk", "limit": 100})
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_arbitrage_bets_missing_region(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /arbitrage-bets without region returns 422."""
    response = await test_client.get("/arbitrage-bets")
    assert response.status_code == 422  # Validation error - region is required


@pytest.mark.asyncio
async def test_list_arbitrage_bets_region_bookmakers(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /arbitrage-bets passes correct bookmakers for region."""
    with patch("app.api.routes.arbitrage.odds_api_provider") as mock_provider:
        mock_provider.get_arbitrage_bets = AsyncMock(return_value=ArbitrageResponse(data=[]))

        response = await test_client.get("/arbitrage-bets", params={"region": "br"})

        assert response.status_code == 200
        call_kwargs = mock_provider.get_arbitrage_bets.call_args[1]
        # Should pass Brazilian bookmakers
        assert "betano" in call_kwargs["bookmakers"]
        assert "pixbet" in call_kwargs["bookmakers"]
