from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings
from app.providers.odds_api import odds_api_provider
from app.schemas.common import Market
from app.schemas.odds_movements import OddsMovementsResponse
from app.services.rate_limiter import limiter

router = APIRouter()


@router.get("")
@limiter.limit(settings.rate_limit_default)
async def get_odds(
    request: Request,
    event_id: str = Query(..., alias="eventId"),
    market: Market = Market.ML,
    bookmakers: str | None = None,
):
    """Get odds for an event."""
    bm_list = bookmakers.split(",") if bookmakers else settings.bookmakers_list
    return await odds_api_provider.get_odds(
        event_id=event_id,
        bookmakers=bm_list,
        market=market.value,
    )


@router.get("/multi")
@limiter.limit(settings.rate_limit_heavy)
async def get_odds_multi(
    request: Request,
    event_ids: str = Query(..., alias="eventIds", description="Comma-separated event IDs (max 10)"),
    market: Market = Market.ML,
    bookmakers: str | None = None,
):
    """Get odds for multiple events in one request.

    Useful for batch operations to reduce API quota usage.
    Limited to 10 events per request.
    """
    ids_list = [eid.strip() for eid in event_ids.split(",") if eid.strip()]
    if not ids_list:
        raise HTTPException(status_code=400, detail="At least one event ID is required")
    if len(ids_list) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 events per request")

    bm_list = bookmakers.split(",") if bookmakers else settings.bookmakers_list
    return await odds_api_provider.get_odds_multi(
        event_ids=ids_list,
        bookmakers=bm_list,
        market=market.value,
    )


@router.get("/updated")
@limiter.limit(settings.rate_limit_default)
async def get_odds_updated(
    request: Request,
    since: int = Query(..., description="Unix timestamp (seconds) - only return odds updated after this time"),
    bookmaker: str | None = None,
    sport: str | None = None,
    market: str = "ML",
):
    """Get odds that changed since a timestamp.

    Useful for efficient polling without fetching all odds repeatedly.
    Returns only odds entries that have been modified after the given timestamp.
    """
    return await odds_api_provider.get_odds_updated(
        since=since,
        bookmaker=bookmaker,
        sport=sport,
        market=market,
    )


@router.get("/movements", response_model=OddsMovementsResponse)
@limiter.limit(settings.rate_limit_default)
async def get_odds_movements(
    request: Request,
    event_id: str = Query(..., alias="eventId"),
    bookmaker: str | None = None,
    market: str = "ML",
):
    """Get historical odds movements for an event."""
    bm = bookmaker or settings.bookmakers_list[0]
    result = await odds_api_provider.get_odds_movements(
        event_id=event_id,
        bookmaker=bm,
        market=market,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="No odds movements found for this event")
    return result
