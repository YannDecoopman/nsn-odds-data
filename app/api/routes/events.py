from fastapi import APIRouter, Query

from app.providers.odds_api import odds_api_provider
from app.schemas.events import (
    EventListResponse,
    EventStatus,
    LiveEventsResponse,
    PaginationInfo,
)

router = APIRouter()


@router.get("", response_model=EventListResponse)
async def list_events(
    sport: str | None = None,
    league: str | None = None,
    status: EventStatus | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(20, le=100),
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
async def list_live_events(
    sport: str | None = None,
    limit: int = Query(20, le=100),
):
    """Get live events with scores."""
    events = await odds_api_provider.get_live_events(sport=sport)
    return LiveEventsResponse(data=events[:limit])
