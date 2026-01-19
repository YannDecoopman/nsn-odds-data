from datetime import datetime, timedelta

from fastapi import APIRouter, Query, Request

from app.config import settings
from app.providers.odds_api import odds_api_provider
from app.schemas.events import (
    EventListResponse,
    EventResponse,
    EventStatus,
    LiveEventsResponse,
    PaginationInfo,
)
from app.services.cache import CACHE_KEY_UPCOMING, cache_service
from app.services.rate_limiter import limiter

router = APIRouter()


@router.get("", response_model=EventListResponse)
@limiter.limit(settings.rate_limit_default)
async def list_events(
    request: Request,
    sport: str | None = None,
    league: str | None = None,
    status: EventStatus | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(100, le=2000),
    offset: int = Query(0, ge=0),
):
    """Get events with filters and pagination."""
    events, total = await odds_api_provider.get_events(
        sport=sport,
        league=league,
        status=status.value if status else None,
        date_from=date_from,
        date_to=date_to,
    )

    # Apply pagination
    paginated = events[offset : offset + limit]

    return EventListResponse(
        data=paginated,
        pagination=PaginationInfo(total=total, limit=limit, offset=offset),
    )


@router.get("/live", response_model=LiveEventsResponse)
@limiter.limit(settings.rate_limit_default)
async def list_live_events(
    request: Request,
    sport: str | None = None,
    limit: int = Query(20, le=100),
):
    """Get live events with scores."""
    events = await odds_api_provider.get_live_events(sport=sport)
    return LiveEventsResponse(data=events[:limit])


@router.get("/search", response_model=EventListResponse)
@limiter.limit(settings.rate_limit_search)
async def search_events(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query (team name)"),
    sport: str = Query("football", description="Sport to search in"),
    limit: int = Query(10, le=50),
):
    """Search events by team name.

    Performs case-insensitive search on home_team and away_team fields.
    """
    # Get events for sport (required by Odds-API.io)
    events, _ = await odds_api_provider.get_events(sport=sport)

    # Filter by search query (case-insensitive)
    query_lower = q.lower()
    filtered = [
        e
        for e in events
        if query_lower in e.home.lower() or query_lower in e.away.lower()
    ]

    # Limit results
    results = filtered[:limit]

    return EventListResponse(
        data=results,
        pagination=PaginationInfo(total=len(filtered), limit=limit, offset=0),
    )


@router.get("/upcoming", response_model=EventListResponse)
@limiter.limit(settings.rate_limit_default)
async def get_upcoming_events(
    request: Request,
    leagues: str | None = Query(
        None, description="Comma-separated league filter (overrides default major leagues)"
    ),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """Get upcoming events from major leagues (cached hourly).

    Returns events from the next 7 days for major football leagues.
    Data is cached and refreshed hourly by a background job.
    """
    # Try to get from cache
    cached = await cache_service.get(CACHE_KEY_UPCOMING)

    if cached:
        events = [EventResponse(**e) for e in cached]
    else:
        # Cache miss - fetch directly (fallback)
        events = await _fetch_upcoming_events()
        # Cache for 1 hour
        await cache_service.set(
            CACHE_KEY_UPCOMING,
            [e.model_dump(mode="json") for e in events],
            ttl=settings.cache_ttl_upcoming,
        )

    # Filter by leagues if specified (override default major leagues)
    if leagues:
        league_list = [lg.strip() for lg in leagues.split(",")]
        events = [e for e in events if e.league.name in league_list]

    total = len(events)

    # Apply pagination
    paginated = events[offset : offset + limit]

    return EventListResponse(
        data=paginated,
        pagination=PaginationInfo(total=total, limit=limit, offset=offset),
    )


@router.get("/{event_id}", response_model=EventResponse)
@limiter.limit(settings.rate_limit_default)
async def get_event_by_id(
    request: Request,
    event_id: str,
):
    """Get a single event by its ID."""
    from app.exceptions import EventNotFoundError

    event = await odds_api_provider.get_event(event_id)
    if event is None:
        raise EventNotFoundError(event_id=event_id)
    return event


async def _fetch_upcoming_events() -> list[EventResponse]:
    """Fetch upcoming events for major leagues."""
    now = datetime.now()
    date_from = now.strftime("%Y-%m-%d")
    date_to = (now + timedelta(days=7)).strftime("%Y-%m-%d")

    events, _ = await odds_api_provider.get_events(
        sport="football",
        date_from=date_from,
        date_to=date_to,
    )

    # Filter by major leagues
    filtered = [e for e in events if e.league.name in settings.major_leagues]

    # Sort by date
    filtered.sort(key=lambda e: e.date)

    return filtered
