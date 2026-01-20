"""Tests for odds routes."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas import (
    BookmakerOdds,
    EventData,
    OddsMetadata,
    OddsOutput,
    OddsValues,
)
from app.schemas.odds_movements import OddsMovementsResponse, OddsSnapshot


@pytest.mark.asyncio
async def test_get_odds_success(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds returns odds for event."""
    odds_output = OddsOutput(
        event=EventData(
            id="evt_123",
            sport="football",
            league="Premier League",
            league_id="pl",
            home_team="Team A",
            away_team="Team B",
            commence_time=datetime(2026, 1, 20, 15, 0, 0),
        ),
        market="1x2",
        bookmakers=[
            BookmakerOdds(
                key="bet365",
                name="Bet365",
                odds=OddsValues(home=1.80, draw=3.50, away=4.20),
                updated_at=datetime(2026, 1, 18, 10, 0, 0),
            ),
        ],
        metadata=OddsMetadata(
            generated_at=datetime(2026, 1, 18, 10, 0, 0),
            is_ended=False,
            hash="abc123",
        ),
    )

    with patch("app.api.routes.odds.odds_api_provider") as mock_provider:
        mock_provider.get_odds = AsyncMock(return_value=odds_output)

        response = await test_client.get("/odds", params={"eventId": "evt_123", "region": "uk"})

        assert response.status_code == 200
        data = response.json()
        assert data["event"]["id"] == "evt_123"
        assert len(data["bookmakers"]) == 1
        assert data["bookmakers"][0]["key"] == "bet365"


@pytest.mark.asyncio
async def test_get_odds_with_market(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds with market parameter."""
    with patch("app.api.routes.odds.odds_api_provider") as mock_provider:
        mock_provider.get_odds = AsyncMock(return_value=None)

        response = await test_client.get(
            "/odds", params={"eventId": "evt_123", "region": "uk", "market": "asian_handicap"}
        )

        # Even if no odds returned, request should succeed
        assert response.status_code == 200 or response.status_code == 204


@pytest.mark.asyncio
async def test_get_odds_with_bookmakers(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds with custom bookmakers list (must be allowed in region)."""
    with patch("app.api.routes.odds.odds_api_provider") as mock_provider:
        mock_provider.get_odds = AsyncMock(return_value=None)

        # bet365 and betfair are allowed in UK region
        response = await test_client.get(
            "/odds", params={"eventId": "evt_123", "region": "uk", "bookmakers": "bet365,betfair"}
        )

        # Verify custom bookmakers were passed
        mock_provider.get_odds.assert_called_once()


@pytest.mark.asyncio
async def test_get_odds_missing_event_id(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds without eventId returns 422."""
    response = await test_client.get("/odds", params={"region": "uk"})
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_odds_missing_region(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds without region returns 422."""
    response = await test_client.get("/odds", params={"eventId": "evt_123"})
    assert response.status_code == 422  # Validation error - region is required


@pytest.mark.asyncio
async def test_get_odds_invalid_region(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds with invalid region returns 422."""
    response = await test_client.get("/odds", params={"eventId": "evt_123", "region": "xx"})
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_odds_bookmaker_not_in_region(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds with bookmaker not allowed in region returns 400."""
    # bet365 is NOT allowed in Brazil region
    response = await test_client.get(
        "/odds", params={"eventId": "evt_123", "region": "br", "bookmakers": "bet365"}
    )
    assert response.status_code == 400
    assert "not available" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_odds_movements_success(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds/movements returns movements."""
    movements_response = OddsMovementsResponse(
        eventId="evt_123",
        bookmaker="Bet365",
        market="ML",
        opening=OddsSnapshot(
            home=1.90, draw=3.60, away=4.50, timestamp=datetime(2026, 1, 15, 10, 0, 0)
        ),
        latest=OddsSnapshot(
            home=1.80, draw=3.50, away=4.20, timestamp=datetime(2026, 1, 18, 10, 0, 0)
        ),
        movements=[
            OddsSnapshot(
                home=1.90, draw=3.60, away=4.50, timestamp=datetime(2026, 1, 15, 10, 0, 0)
            ),
            OddsSnapshot(
                home=1.85, draw=3.55, away=4.35, timestamp=datetime(2026, 1, 16, 10, 0, 0)
            ),
            OddsSnapshot(
                home=1.80, draw=3.50, away=4.20, timestamp=datetime(2026, 1, 18, 10, 0, 0)
            ),
        ],
    )

    with patch("app.api.routes.odds.odds_api_provider") as mock_provider:
        mock_provider.get_odds_movements = AsyncMock(return_value=movements_response)

        response = await test_client.get("/odds/movements", params={"eventId": "evt_123", "region": "uk"})

        assert response.status_code == 200
        data = response.json()
        assert data["eventId"] == "evt_123"
        assert data["opening"]["home"] == 1.90
        assert data["latest"]["home"] == 1.80
        assert len(data["movements"]) == 3


@pytest.mark.asyncio
async def test_get_odds_movements_not_found(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds/movements returns 404 when no data."""
    with patch("app.api.routes.odds.odds_api_provider") as mock_provider:
        mock_provider.get_odds_movements = AsyncMock(return_value=None)

        response = await test_client.get("/odds/movements", params={"eventId": "evt_999", "region": "uk"})

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_odds_movements_with_bookmaker(
    test_client, mock_cache_service, mock_metrics_service
):
    """Test GET /odds/movements with custom bookmaker."""
    movements_response = OddsMovementsResponse(
        eventId="evt_123",
        bookmaker="Betano",
        market="ML",
        opening=OddsSnapshot(home=1.85, draw=3.55, away=4.40, timestamp=datetime(2026, 1, 15)),
        latest=OddsSnapshot(home=1.80, draw=3.50, away=4.20, timestamp=datetime(2026, 1, 18)),
        movements=[],
    )

    with patch("app.api.routes.odds.odds_api_provider") as mock_provider:
        mock_provider.get_odds_movements = AsyncMock(return_value=movements_response)

        # betano is allowed in Brazil region
        response = await test_client.get(
            "/odds/movements", params={"eventId": "evt_123", "region": "br", "bookmaker": "betano"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["bookmaker"] == "Betano"


@pytest.mark.asyncio
async def test_get_odds_movements_with_market(
    test_client, mock_cache_service, mock_metrics_service
):
    """Test GET /odds/movements with market parameter."""
    movements_response = OddsMovementsResponse(
        eventId="evt_123",
        bookmaker="Bet365",
        market="Totals",
        opening=OddsSnapshot(home=1.90, away=1.90, timestamp=datetime(2026, 1, 15)),
        latest=OddsSnapshot(home=1.85, away=1.95, timestamp=datetime(2026, 1, 18)),
        movements=[],
    )

    with patch("app.api.routes.odds.odds_api_provider") as mock_provider:
        mock_provider.get_odds_movements = AsyncMock(return_value=movements_response)

        response = await test_client.get(
            "/odds/movements", params={"eventId": "evt_123", "region": "uk", "market": "Totals"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["market"] == "Totals"


@pytest.mark.asyncio
async def test_get_odds_multi_success(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds/multi returns batch odds."""
    odds_output = OddsOutput(
        event=EventData(
            id="evt_123",
            sport="football",
            league="Premier League",
            league_id="pl",
            home_team="Team A",
            away_team="Team B",
            commence_time=datetime(2026, 1, 20, 15, 0, 0),
        ),
        market="1x2",
        bookmakers=[
            BookmakerOdds(
                key="bet365",
                name="Bet365",
                odds=OddsValues(home=1.80, draw=3.50, away=4.20),
                updated_at=datetime(2026, 1, 18, 10, 0, 0),
            ),
        ],
        metadata=OddsMetadata(
            generated_at=datetime(2026, 1, 18, 10, 0, 0),
            is_ended=False,
            hash="abc123",
        ),
    )

    with patch("app.api.routes.odds.odds_api_provider") as mock_provider:
        mock_provider.get_odds_multi = AsyncMock(return_value=[odds_output, odds_output])

        response = await test_client.get("/odds/multi", params={"eventIds": "evt_123,evt_456", "region": "uk"})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


@pytest.mark.asyncio
async def test_get_odds_multi_empty_ids(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds/multi with empty event IDs returns 400."""
    response = await test_client.get("/odds/multi", params={"eventIds": "", "region": "uk"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_odds_multi_too_many_ids(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds/multi with more than 10 IDs returns 400."""
    ids = ",".join([f"evt_{i}" for i in range(15)])
    response = await test_client.get("/odds/multi", params={"eventIds": ids, "region": "uk"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_odds_multi_missing_param(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds/multi without eventIds returns 422."""
    response = await test_client.get("/odds/multi", params={"region": "uk"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_odds_updated_success(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds/updated returns updated odds."""
    updated_data = [
        {"eventId": "evt_123", "bookmaker": "Bet365", "odds": {"home": 1.80}},
        {"eventId": "evt_456", "bookmaker": "Betano", "odds": {"home": 2.10}},
    ]

    with patch("app.api.routes.odds.odds_api_provider") as mock_provider:
        mock_provider.get_odds_updated = AsyncMock(return_value=updated_data)

        response = await test_client.get("/odds/updated", params={"since": 1737200000, "region": "uk"})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


@pytest.mark.asyncio
async def test_get_odds_updated_with_filters(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds/updated with optional filters."""
    with patch("app.api.routes.odds.odds_api_provider") as mock_provider:
        mock_provider.get_odds_updated = AsyncMock(return_value=[])

        response = await test_client.get(
            "/odds/updated",
            params={"since": 1737200000, "region": "uk", "bookmaker": "bet365", "sport": "football", "market": "ML"},
        )

        assert response.status_code == 200
        mock_provider.get_odds_updated.assert_called_once_with(
            since=1737200000, bookmaker="bet365", sport="football", market="ML"
        )


@pytest.mark.asyncio
async def test_get_odds_updated_missing_since(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds/updated without since returns 422."""
    response = await test_client.get("/odds/updated", params={"region": "uk"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_odds_updated_bookmaker_not_in_region(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /odds/updated with bookmaker not in region returns 400."""
    response = await test_client.get(
        "/odds/updated", params={"since": 1737200000, "region": "br", "bookmaker": "bet365"}
    )
    assert response.status_code == 400
