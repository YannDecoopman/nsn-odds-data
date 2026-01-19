from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings
from app.providers.odds_api import odds_api_provider
from app.schemas.participants import ParticipantResponse, ParticipantsListResponse
from app.services.rate_limiter import limiter

router = APIRouter()


@router.get("", response_model=ParticipantsListResponse)
@limiter.limit(settings.rate_limit_default)
async def list_participants(
    request: Request,
    sport: str = Query(..., description="Sport slug (e.g., football, basketball)"),
    search: str | None = Query(None, description="Search query for team name"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    """List teams/participants for a sport.

    Optionally filter by name using the search parameter.
    """
    participants = await odds_api_provider.get_participants(sport=sport, search=search)

    # Transform to response format
    items = [
        ParticipantResponse(
            id=str(p.get("id", "")),
            name=p.get("name", ""),
            slug=p.get("slug", p.get("name", "").lower().replace(" ", "-")),
            sport=p.get("sport", sport),
            country=p.get("country"),
            logo=p.get("logo"),
        )
        for p in participants
    ]

    total = len(items)
    paginated = items[offset : offset + limit]

    return ParticipantsListResponse(data=paginated, total=total)


@router.get("/{participant_id}", response_model=ParticipantResponse)
@limiter.limit(settings.rate_limit_default)
async def get_participant(
    request: Request,
    participant_id: str,
):
    """Get a single participant by ID."""
    participant = await odds_api_provider.get_participant(participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")

    return ParticipantResponse(
        id=str(participant.get("id", participant_id)),
        name=participant.get("name", ""),
        slug=participant.get("slug", participant.get("name", "").lower().replace(" ", "-")),
        sport=participant.get("sport", ""),
        country=participant.get("country"),
        logo=participant.get("logo"),
    )
