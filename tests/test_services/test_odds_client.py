"""Tests for OddsAPIClient service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.exceptions import ProviderError, ProviderTimeoutError, RateLimitError
from app.services.odds_client import OddsAPIClient


@pytest.fixture
def odds_client():
    """Create OddsAPIClient instance."""
    with patch("app.services.odds_client.settings") as mock_settings:
        mock_settings.odds_api_base_url = "https://api.test.com/v3"
        mock_settings.odds_api_key = "test_api_key"
        mock_settings.cache_ttl_sports = 86400
        mock_settings.cache_ttl_events = 300
        mock_settings.bookmakers_list = ["bet365", "betano"]
        yield OddsAPIClient()


@pytest.mark.asyncio
async def test_request_success(odds_client):
    """Test _request makes successful HTTP call."""
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": "123"}]
    mock_response.raise_for_status = MagicMock()

    with (
        patch("httpx.AsyncClient") as mock_client_class,
        patch("app.services.odds_client.cache_service") as mock_cache,
        patch("app.services.odds_client.metrics_service") as mock_metrics,
    ):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock()

        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_metrics.track_api_call = AsyncMock()

        result = await odds_client._request("/sports")

        assert result == [{"id": "123"}]
        mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_request_with_cache_hit(odds_client):
    """Test _request returns cached data."""
    with patch("app.services.odds_client.cache_service") as mock_cache:
        mock_cache.get = AsyncMock(return_value=[{"cached": True}])

        result = await odds_client._request("/sports", cache_key="sports:all")

        assert result == [{"cached": True}]


def test_provider_timeout_error_structure():
    """Test ProviderTimeoutError has correct structure."""
    error = ProviderTimeoutError(
        "Request timed out",
        timeout_seconds=30.0,
        endpoint="/events",
    )

    assert error.message == "Request timed out"
    assert error.code == "PROVIDER_TIMEOUT"
    assert error.details["timeout_seconds"] == 30.0
    assert error.details["endpoint"] == "/events"


def test_rate_limit_error_structure():
    """Test RateLimitError has correct structure."""
    error = RateLimitError(
        "Rate limit exceeded",
        retry_after=60,
        remaining_requests=0,
    )

    assert error.message == "Rate limit exceeded"
    assert error.code == "RATE_LIMIT_EXCEEDED"
    assert error.retry_after == 60
    assert error.details["retry_after"] == 60


def test_provider_error_structure():
    """Test ProviderError has correct structure."""
    error = ProviderError(
        "HTTP 500 error",
        status_code=500,
        response_body="Internal server error",
        endpoint="/events",
    )

    assert error.message == "HTTP 500 error"
    assert error.code == "PROVIDER_ERROR"
    assert error.status_code == 500
    assert error.details["status_code"] == 500


@pytest.mark.asyncio
async def test_get_sports(odds_client):
    """Test get_sports returns sports list."""
    sports_data = [{"name": "Football", "slug": "football", "active": True}]

    with patch.object(odds_client, "_request", AsyncMock(return_value=sports_data)):
        result = await odds_client.get_sports()

        assert len(result) == 1
        assert result[0]["name"] == "Football"


@pytest.mark.asyncio
async def test_get_bookmakers(odds_client):
    """Test get_bookmakers returns bookmakers list."""
    bookmakers_data = [{"key": "bet365", "name": "Bet365"}]

    with patch.object(odds_client, "_request", AsyncMock(return_value=bookmakers_data)):
        result = await odds_client.get_bookmakers()

        assert len(result) == 1
        assert result[0]["key"] == "bet365"


@pytest.mark.asyncio
async def test_get_events(odds_client):
    """Test get_events returns parsed events."""
    events_data = [
        {
            "id": "evt_123",
            "home": "Team A",
            "away": "Team B",
            "date": "2026-01-20T15:00:00Z",
            "status": "not_started",
            "sport": {"name": "Football", "slug": "football"},
            "league": {"name": "Premier League", "slug": "premier-league"},
        }
    ]

    with patch.object(odds_client, "_request", AsyncMock(return_value=events_data)):
        events, total = await odds_client.get_events(sport="football")

        assert total == 1
        assert len(events) == 1
        assert events[0].id == "evt_123"
        assert events[0].home == "Team A"


@pytest.mark.asyncio
async def test_get_events_empty(odds_client):
    """Test get_events handles empty response."""
    with patch.object(odds_client, "_request", AsyncMock(return_value=None)):
        events, total = await odds_client.get_events()

        assert total == 0
        assert events == []


@pytest.mark.asyncio
async def test_get_live_events(odds_client):
    """Test get_live_events returns live events."""
    events_data = [
        {
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
    ]

    with patch.object(odds_client, "_request", AsyncMock(return_value=events_data)):
        result = await odds_client.get_live_events(sport="football")

        assert len(result) == 1
        assert result[0].id == "evt_456"
        assert result[0].scores.home == 1


@pytest.mark.asyncio
async def test_get_leagues(odds_client):
    """Test get_leagues returns leagues list."""
    leagues_data = [{"name": "Premier League", "slug": "premier-league"}]

    with patch.object(odds_client, "_request", AsyncMock(return_value=leagues_data)):
        result = await odds_client.get_leagues(sport="football")

        assert len(result) == 1
        assert result[0]["name"] == "Premier League"


@pytest.mark.asyncio
async def test_get_odds(odds_client):
    """Test get_odds returns transformed odds."""
    odds_data = {
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
            ]
        },
    }

    with patch.object(odds_client, "_request", AsyncMock(return_value=odds_data)):
        result = await odds_client.get_odds(
            event_id="evt_123",
            bookmakers=["bet365"],
            market="1x2",
        )

        assert result is not None
        assert result.event.id == "evt_123"
        assert len(result.bookmakers) == 1
        assert result.bookmakers[0].odds.home == 1.80


@pytest.mark.asyncio
async def test_get_odds_no_data(odds_client):
    """Test get_odds returns None when no data."""
    with patch.object(odds_client, "_request", AsyncMock(return_value=None)):
        result = await odds_client.get_odds(
            event_id="evt_999",
            bookmakers=["bet365"],
        )

        assert result is None


@pytest.mark.asyncio
async def test_transform_asian_handicap(odds_client):
    """Test _transform_asian_handicap transforms data correctly."""
    data = {
        "id": "evt_123",
        "home": "Team A",
        "away": "Team B",
        "date": "2026-01-20T15:00:00Z",
        "sport": {"name": "Football", "slug": "football"},
        "league": {"name": "Premier League", "slug": "premier-league"},
        "bookmakers": {
            "Bet365": [
                {
                    "name": "Asian Handicap",
                    "updatedAt": "2026-01-18T10:00:00Z",
                    "odds": [
                        {"hdp": -0.5, "home": "1.85", "away": "2.05"},
                        {"hdp": -1.0, "home": "2.10", "away": "1.80"},
                    ],
                }
            ]
        },
    }

    result = odds_client._transform_asian_handicap(data)

    assert result is not None
    assert result.market == "asian_handicap"
    assert len(result.bookmakers) == 1
    assert len(result.bookmakers[0].lines) == 2
    # Lines are sorted by hdp, so -1.0 comes before -0.5
    assert result.bookmakers[0].lines[0].hdp == -1.0
    assert result.bookmakers[0].lines[1].hdp == -0.5


@pytest.mark.asyncio
async def test_transform_totals(odds_client):
    """Test _transform_totals transforms data correctly."""
    data = {
        "id": "evt_123",
        "home": "Team A",
        "away": "Team B",
        "date": "2026-01-20T15:00:00Z",
        "sport": {"slug": "football"},
        "league": {"name": "Premier League"},
        "bookmakers": {
            "Bet365": [
                {
                    "name": "Totals",
                    "updatedAt": "2026-01-18T10:00:00Z",
                    "odds": [
                        {"line": 2.5, "over": "1.90", "under": "1.95"},
                    ],
                }
            ]
        },
    }

    result = odds_client._transform_totals(data)

    assert result is not None
    assert result.market == "totals"
    assert result.bookmakers[0].lines[0].line == 2.5


@pytest.mark.asyncio
async def test_transform_btts(odds_client):
    """Test _transform_btts transforms data correctly."""
    data = {
        "id": "evt_123",
        "home": "Team A",
        "away": "Team B",
        "date": "2026-01-20T15:00:00Z",
        "sport": {"slug": "football"},
        "league": {"name": "Premier League"},
        "bookmakers": {
            "Bet365": [
                {
                    "name": "Both Teams to Score",
                    "updatedAt": "2026-01-18T10:00:00Z",
                    "odds": [{"yes": "1.85", "no": "1.95"}],
                }
            ]
        },
    }

    result = odds_client._transform_btts(data)

    assert result is not None
    assert result.market == "btts"
    assert result.bookmakers[0].odds.yes == 1.85


@pytest.mark.asyncio
async def test_get_value_bets(odds_client):
    """Test get_value_bets returns aggregated value bets."""
    value_bets_data = [
        {
            "id": "vb_123",
            "expectedValue": 5.5,
            "expectedValueUpdatedAt": "2026-01-18T10:00:00Z",
            "betSide": "home",
            "market": {"name": "ML", "home": "1.95"},
            "bookmaker": "Bet365",
            "bookmakerOdds": {"home": "2.10", "away": "3.80"},
            "eventId": 123,
            "event": {
                "home": "Team A",
                "away": "Team B",
                "date": "2026-01-20T15:00:00Z",
                "sport": "Football",
                "league": "Premier League",
            },
        }
    ]

    with patch.object(
        odds_client, "get_value_bets_for_bookmaker", AsyncMock(return_value=value_bets_data)
    ):
        result = await odds_client.get_value_bets(
            bookmakers=["bet365"],
            min_ev=2.0,
            limit=10,
        )

        assert len(result.data) == 1
        assert result.data[0].expected_value == 5.5


@pytest.mark.asyncio
async def test_get_arbitrage_bets(odds_client):
    """Test get_arbitrage_bets returns arbitrage opportunities."""
    arb_data = [
        {
            "id": "arb_456",
            "eventId": 456,
            "market": {"name": "ML"},
            "profitMargin": 2.5,
            "impliedProbability": 97.5,
            "totalStake": 100,
            "legs": [
                {"side": "home", "bookmaker": "Bet365", "odds": 2.10},
                {"side": "away", "bookmaker": "Betano", "odds": 2.20},
            ],
            "optimalStakes": [],
            "event": {
                "home": "Team E",
                "away": "Team F",
                "date": "2026-01-21T18:00:00Z",
                "sport": "Football",
                "league": "Serie A",
            },
            "detectedAt": "2026-01-18T12:00:00Z",
        }
    ]

    with patch.object(odds_client, "_request", AsyncMock(return_value=arb_data)):
        result = await odds_client.get_arbitrage_bets(
            bookmakers=["bet365", "betano"],
            min_profit=1.0,
            limit=5,
        )

        assert len(result.data) == 1
        assert result.data[0].profit_margin == 2.5


@pytest.mark.asyncio
async def test_get_odds_movements(odds_client):
    """Test get_odds_movements returns movement history."""
    movements_data = {
        "eventId": "evt_123",
        "bookmaker": "Bet365",
        "market": "ML",
        "opening": {"home": 1.90, "draw": 3.60, "away": 4.50, "timestamp": "2026-01-15T10:00:00Z"},
        "latest": {"home": 1.80, "draw": 3.50, "away": 4.20, "timestamp": "2026-01-18T10:00:00Z"},
        "movements": [
            {"home": 1.90, "draw": 3.60, "away": 4.50, "timestamp": "2026-01-15T10:00:00Z"},
        ],
    }

    with patch.object(odds_client, "_request", AsyncMock(return_value=movements_data)):
        result = await odds_client.get_odds_movements(
            event_id="evt_123",
            bookmaker="Bet365",
            market="ML",
        )

        assert result is not None
        assert result.event_id == "evt_123"
        assert result.opening.home == 1.90
        assert result.latest.home == 1.80
