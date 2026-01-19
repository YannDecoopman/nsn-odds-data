"""Tests for events routes."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.events import EventResponse, EventStatus, LeagueInfo, SportInfo


@pytest.mark.asyncio
async def test_list_events_success(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events returns events list."""
    sample_event = EventResponse(
        id="evt_123",
        home="Team A",
        away="Team B",
        date=datetime(2026, 1, 20, 15, 0, 0),
        status=EventStatus.NOT_STARTED,
        sport=SportInfo(name="Football", slug="football"),
        league=LeagueInfo(name="Premier League", slug="premier-league"),
    )

    with patch("app.api.routes.events.odds_api_provider") as mock_provider:
        mock_provider.get_events = AsyncMock(return_value=([sample_event], 1))

        response = await test_client.get("/events")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "evt_123"
        assert data["data"][0]["home"] == "Team A"
        assert data["pagination"]["total"] == 1


@pytest.mark.asyncio
async def test_list_events_with_sport_filter(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events with sport filter."""
    with patch("app.api.routes.events.odds_api_provider") as mock_provider:
        mock_provider.get_events = AsyncMock(return_value=([], 0))

        response = await test_client.get("/events", params={"sport": "football"})

        assert response.status_code == 200
        mock_provider.get_events.assert_called_once()
        call_kwargs = mock_provider.get_events.call_args[1]
        assert call_kwargs["sport"] == "football"


@pytest.mark.asyncio
async def test_list_events_with_pagination(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events with pagination params."""
    events = [
        EventResponse(
            id=f"evt_{i}",
            home=f"Team {i}A",
            away=f"Team {i}B",
            date=datetime(2026, 1, 20, 15, 0, 0),
            status=EventStatus.NOT_STARTED,
            sport=SportInfo(name="Football", slug="football"),
            league=LeagueInfo(name="Premier League", slug="premier-league"),
        )
        for i in range(10)
    ]

    with patch("app.api.routes.events.odds_api_provider") as mock_provider:
        mock_provider.get_events = AsyncMock(return_value=(events, 10))

        response = await test_client.get("/events", params={"limit": 5, "offset": 2})

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["limit"] == 5
        assert data["pagination"]["offset"] == 2
        assert len(data["data"]) == 5


@pytest.mark.asyncio
async def test_list_events_with_date_filter(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events with date filters."""
    with patch("app.api.routes.events.odds_api_provider") as mock_provider:
        mock_provider.get_events = AsyncMock(return_value=([], 0))

        response = await test_client.get(
            "/events",
            params={"date_from": "2026-01-15", "date_to": "2026-01-20"},
        )

        assert response.status_code == 200
        call_kwargs = mock_provider.get_events.call_args[1]
        assert call_kwargs["date_from"] == "2026-01-15"
        assert call_kwargs["date_to"] == "2026-01-20"


@pytest.mark.asyncio
async def test_list_events_with_status_filter(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events with status filter."""
    with patch("app.api.routes.events.odds_api_provider") as mock_provider:
        mock_provider.get_events = AsyncMock(return_value=([], 0))

        response = await test_client.get("/events", params={"status": "in_progress"})

        assert response.status_code == 200
        call_kwargs = mock_provider.get_events.call_args[1]
        assert call_kwargs["status"] == "in_progress"


@pytest.mark.asyncio
async def test_list_live_events_success(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events/live returns live events."""
    from app.schemas.events import LiveEventResponse, ScoreInfo

    live_event = LiveEventResponse(
        id="evt_456",
        home="Team C",
        away="Team D",
        date=datetime(2026, 1, 18, 14, 0, 0),
        status=EventStatus.IN_PROGRESS,
        sport=SportInfo(name="Football", slug="football"),
        league=LeagueInfo(name="La Liga", slug="la-liga"),
        scores=ScoreInfo(home=1, away=0),
        minute=45,
        period="1H",
    )

    with patch("app.api.routes.events.odds_api_provider") as mock_provider:
        mock_provider.get_live_events = AsyncMock(return_value=[live_event])

        response = await test_client.get("/events/live")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "evt_456"
        assert data["data"][0]["scores"]["home"] == 1


@pytest.mark.asyncio
async def test_list_live_events_with_sport_filter(
    test_client, mock_cache_service, mock_metrics_service
):
    """Test GET /events/live with sport filter."""
    with patch("app.api.routes.events.odds_api_provider") as mock_provider:
        mock_provider.get_live_events = AsyncMock(return_value=[])

        response = await test_client.get("/events/live", params={"sport": "football"})

        assert response.status_code == 200
        mock_provider.get_live_events.assert_called_once_with(sport="football")


@pytest.mark.asyncio
async def test_search_events_success(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events/search returns matching events."""
    event = EventResponse(
        id="evt_789",
        home="Manchester United",
        away="Liverpool",
        date=datetime(2026, 1, 22, 17, 0, 0),
        status=EventStatus.NOT_STARTED,
        sport=SportInfo(name="Football", slug="football"),
        league=LeagueInfo(name="Premier League", slug="premier-league"),
    )

    with patch("app.api.routes.events.odds_api_provider") as mock_provider:
        mock_provider.get_events = AsyncMock(return_value=([event], 1))

        response = await test_client.get(
            "/events/search", params={"q": "manchester", "sport": "football"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert "Manchester" in data["data"][0]["home"]


@pytest.mark.asyncio
async def test_search_events_no_match(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events/search returns empty when no match."""
    event = EventResponse(
        id="evt_789",
        home="Barcelona",
        away="Real Madrid",
        date=datetime(2026, 1, 22, 17, 0, 0),
        status=EventStatus.NOT_STARTED,
        sport=SportInfo(name="Football", slug="football"),
        league=LeagueInfo(name="La Liga", slug="la-liga"),
    )

    with patch("app.api.routes.events.odds_api_provider") as mock_provider:
        mock_provider.get_events = AsyncMock(return_value=([event], 1))

        response = await test_client.get(
            "/events/search", params={"q": "manchester", "sport": "football"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0


@pytest.mark.asyncio
async def test_search_events_query_too_short(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events/search rejects short query."""
    response = await test_client.get("/events/search", params={"q": "a"})
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_upcoming_events_success(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events/upcoming returns cached events."""
    event = EventResponse(
        id="evt_upcoming",
        home="Team X",
        away="Team Y",
        date=datetime(2026, 1, 25, 20, 0, 0),
        status=EventStatus.NOT_STARTED,
        sport=SportInfo(name="Football", slug="football"),
        league=LeagueInfo(name="England - Premier League", slug="premier-league"),
    )

    with patch("app.api.routes.events.cache_service") as mock_cache:
        mock_cache.get = AsyncMock(
            return_value=[
                {
                    "id": "evt_upcoming",
                    "home": "Team X",
                    "away": "Team Y",
                    "date": "2026-01-25T20:00:00",
                    "status": "not_started",
                    "sport": {"name": "Football", "slug": "football"},
                    "league": {"name": "England - Premier League", "slug": "premier-league"},
                }
            ]
        )

        response = await test_client.get("/events/upcoming")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data


@pytest.mark.asyncio
async def test_upcoming_events_cache_miss(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events/upcoming fetches on cache miss."""
    event = EventResponse(
        id="evt_upcoming",
        home="Team X",
        away="Team Y",
        date=datetime(2026, 1, 25, 20, 0, 0),
        status=EventStatus.NOT_STARTED,
        sport=SportInfo(name="Football", slug="football"),
        league=LeagueInfo(name="England - Premier League", slug="premier-league"),
    )

    with (
        patch("app.api.routes.events.cache_service") as mock_cache,
        patch("app.api.routes.events.odds_api_provider") as mock_provider,
    ):
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_provider.get_events = AsyncMock(return_value=([event], 1))

        response = await test_client.get("/events/upcoming")

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_event_by_id_success(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events/{id} returns single event."""
    event = EventResponse(
        id="evt_123",
        home="Team A",
        away="Team B",
        date=datetime(2026, 1, 20, 15, 0, 0),
        status=EventStatus.NOT_STARTED,
        sport=SportInfo(name="Football", slug="football"),
        league=LeagueInfo(name="Premier League", slug="premier-league"),
    )

    with patch("app.api.routes.events.odds_api_provider") as mock_provider:
        mock_provider.get_event = AsyncMock(return_value=event)

        response = await test_client.get("/events/evt_123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "evt_123"
        assert data["home"] == "Team A"


@pytest.mark.asyncio
async def test_get_event_by_id_not_found(test_client, mock_cache_service, mock_metrics_service):
    """Test GET /events/{id} returns 404 for unknown event."""
    with patch("app.api.routes.events.odds_api_provider") as mock_provider:
        mock_provider.get_event = AsyncMock(return_value=None)

        response = await test_client.get("/events/evt_unknown")

        assert response.status_code == 404
