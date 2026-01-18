"""Global fixtures for nsn-odds-data tests."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.events import EventResponse, EventStatus, LeagueInfo, SportInfo


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def test_client():
    """Async test client for FastAPI."""
    # Disable API key auth and rate limiting for tests
    with (
        patch("app.config.settings.api_key_enabled", False),
        patch("app.config.settings.rate_limit_enabled", False),
    ):
        # Also disable the rate limiter directly
        app.state.limiter.enabled = False
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
        app.state.limiter.enabled = True


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_cache_service(mock_redis):
    """Mock cache service."""
    with patch("app.services.cache.cache_service") as mock:
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=None)
        mock.delete = AsyncMock(return_value=None)
        mock.get_client = AsyncMock(return_value=mock_redis)
        yield mock


@pytest.fixture
def mock_metrics_service():
    """Mock metrics service."""
    with patch("app.services.metrics.metrics_service") as mock:
        mock.track_request = AsyncMock()
        mock.track_error = AsyncMock()
        mock.track_latency = AsyncMock()
        mock.track_api_call = AsyncMock()
        mock.track_cache_hit = AsyncMock()
        mock.track_cache_miss = AsyncMock()
        yield mock


@pytest.fixture
def sample_event() -> dict[str, Any]:
    """Sample event data from API."""
    return {
        "id": "evt_123",
        "home": "Team A",
        "away": "Team B",
        "date": "2026-01-20T15:00:00Z",
        "status": "not_started",
        "sport": {"name": "Football", "slug": "football"},
        "league": {"name": "Premier League", "slug": "premier-league"},
    }


@pytest.fixture
def sample_event_response() -> EventResponse:
    """Sample EventResponse object."""
    return EventResponse(
        id="evt_123",
        home="Team A",
        away="Team B",
        date=datetime(2026, 1, 20, 15, 0, 0),
        status=EventStatus.NOT_STARTED,
        sport=SportInfo(name="Football", slug="football"),
        league=LeagueInfo(name="Premier League", slug="premier-league"),
    )


@pytest.fixture
def sample_live_event() -> dict[str, Any]:
    """Sample live event data from API."""
    return {
        "id": "evt_456",
        "home": "Team C",
        "away": "Team D",
        "date": "2026-01-18T14:00:00Z",
        "status": "live",
        "sport": {"name": "Football", "slug": "football"},
        "league": {"name": "La Liga", "slug": "la-liga"},
        "scores": {"home": 1, "away": 0},
        "minute": 45,
        "period": "1H",
    }


@pytest.fixture
def sample_odds() -> dict[str, Any]:
    """Sample odds data from API."""
    return {
        "id": "evt_123",
        "home": "Team A",
        "away": "Team B",
        "date": "2026-01-20T15:00:00Z",
        "sport": {"name": "Football", "slug": "football"},
        "league": {"name": "Premier League", "slug": "premier-league"},
        "bookmakers": {
            "Bet365": [
                {
                    "name": "ML",
                    "updatedAt": "2026-01-18T10:00:00Z",
                    "odds": [{"home": "1.80", "draw": "3.50", "away": "4.20"}],
                }
            ],
            "Betano": [
                {
                    "name": "ML",
                    "updatedAt": "2026-01-18T10:05:00Z",
                    "odds": [{"home": "1.85", "draw": "3.40", "away": "4.00"}],
                }
            ],
        },
    }


@pytest.fixture
def sample_league() -> dict[str, Any]:
    """Sample league data from API."""
    return {
        "name": "Premier League",
        "slug": "premier-league",
        "sport": "football",
    }


@pytest.fixture
def sample_value_bet() -> dict[str, Any]:
    """Sample value bet data from API."""
    return {
        "id": "vb_123_bet365",
        "expectedValue": 5.5,
        "expectedValueUpdatedAt": "2026-01-18T10:00:00Z",
        "betSide": "home",
        "market": {"name": "ML", "home": "1.95", "draw": "3.50", "away": "4.00"},
        "bookmaker": "Bet365",
        "bookmakerOdds": {"home": "2.10", "draw": "3.40", "away": "3.80", "href": "https://bet365.com"},
        "eventId": 123,
        "event": {
            "home": "Team A",
            "away": "Team B",
            "date": "2026-01-20T15:00:00Z",
            "sport": "Football",
            "league": "Premier League",
        },
    }


@pytest.fixture
def sample_arbitrage_bet() -> dict[str, Any]:
    """Sample arbitrage bet data from API."""
    return {
        "id": "arb_456",
        "eventId": 456,
        "market": {"name": "ML"},
        "profitMargin": 2.5,
        "impliedProbability": 97.5,
        "totalStake": 100,
        "legs": [
            {"side": "home", "bookmaker": "Bet365", "odds": 2.10, "directLink": "https://bet365.com"},
            {"side": "away", "bookmaker": "Betano", "odds": 2.20, "directLink": "https://betano.com"},
        ],
        "optimalStakes": [
            {"side": "home", "bookmaker": "Bet365", "stake": 51.2, "potentialReturn": 107.52},
            {"side": "away", "bookmaker": "Betano", "stake": 48.8, "potentialReturn": 107.36},
        ],
        "event": {
            "home": "Team E",
            "away": "Team F",
            "date": "2026-01-21T18:00:00Z",
            "sport": "Football",
            "league": "Serie A",
        },
        "detectedAt": "2026-01-18T12:00:00Z",
    }


@pytest.fixture
def sample_odds_movements() -> dict[str, Any]:
    """Sample odds movements data from API."""
    return {
        "eventId": "evt_123",
        "bookmaker": "Bet365",
        "market": "ML",
        "opening": {"home": 1.90, "draw": 3.60, "away": 4.50, "timestamp": "2026-01-15T10:00:00Z"},
        "latest": {"home": 1.80, "draw": 3.50, "away": 4.20, "timestamp": "2026-01-18T10:00:00Z"},
        "movements": [
            {"home": 1.90, "draw": 3.60, "away": 4.50, "timestamp": "2026-01-15T10:00:00Z"},
            {"home": 1.85, "draw": 3.55, "away": 4.35, "timestamp": "2026-01-16T10:00:00Z"},
            {"home": 1.80, "draw": 3.50, "away": 4.20, "timestamp": "2026-01-18T10:00:00Z"},
        ],
    }


@pytest.fixture
def mock_odds_api_provider(
    sample_event,
    sample_event_response,
    sample_live_event,
    sample_odds,
    sample_league,
    sample_value_bet,
    sample_arbitrage_bet,
    sample_odds_movements,
):
    """Mock the OddsAPIProvider for route tests."""
    with patch("app.providers.odds_api.odds_api_provider") as mock:
        # Events
        mock.get_events = AsyncMock(return_value=([sample_event_response], 1))
        mock.get_live_events = AsyncMock(return_value=[])

        # Leagues
        mock.get_leagues = AsyncMock(return_value=[sample_league])

        # Odds - return properly structured mock
        mock.get_odds = AsyncMock(return_value=None)
        mock.get_odds_movements = AsyncMock(return_value=None)

        # Value bets
        from app.schemas.value_bets import ValueBetsResponse

        mock.get_value_bets = AsyncMock(return_value=ValueBetsResponse(data=[]))

        # Arbitrage
        from app.schemas.arbitrage import ArbitrageResponse

        mock.get_arbitrage_bets = AsyncMock(return_value=ArbitrageResponse(data=[]))

        # Sports
        mock.get_sports = AsyncMock(
            return_value=[{"name": "Football", "slug": "football", "active": True}]
        )

        yield mock


@pytest.fixture
def mock_odds_client(sample_event, sample_odds, sample_league):
    """Mock the OddsAPIClient for service tests."""
    with patch("app.services.odds_client.odds_client") as mock:
        mock._request = AsyncMock(return_value=[sample_event])
        mock.get_events = AsyncMock(return_value=([], 0))
        mock.get_live_events = AsyncMock(return_value=[])
        mock.get_leagues = AsyncMock(return_value=[sample_league])
        mock.get_odds = AsyncMock(return_value=None)
        mock.get_sports = AsyncMock(return_value=[])
        mock.get_bookmakers = AsyncMock(return_value=[])
        yield mock


@pytest.fixture
def mock_httpx():
    """Mock httpx.AsyncClient for HTTP tests."""
    with patch("httpx.AsyncClient") as mock_class:
        mock_client = AsyncMock()
        mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_client
