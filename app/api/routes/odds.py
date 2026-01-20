from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings
from app.providers.odds_api import odds_api_provider
from app.schemas.common import Market, Region
from app.schemas.odds_movements import OddsMovementsResponse
from app.services.rate_limiter import limiter
from app.services.region_filter import (
    get_allowed_bookmakers,
    get_bookmakers_for_region,
    validate_bookmaker_access,
)

router = APIRouter()


@router.get("")
@limiter.limit(settings.rate_limit_default)
async def get_odds(
    request: Request,
    event_id: str = Query(..., alias="eventId"),
    region: Region = Query(..., description="Region code (br, fr, uk, es, it, de, mx, ar, co)"),
    market: Market = Market.ML,
    bookmakers: str | None = Query(None, description="Comma-separated bookmakers (must be allowed in region)"),
):
    """Get odds for an event, filtered by region.

    The region parameter is required and determines which bookmakers are available.
    If specific bookmakers are requested, they must be allowed in the region.
    """
    requested_bm = bookmakers.split(",") if bookmakers else None
    bm_list = get_bookmakers_for_region(region, requested_bm)

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
    region: Region = Query(..., description="Region code (br, fr, uk, es, it, de, mx, ar, co)"),
    market: Market = Market.ML,
    bookmakers: str | None = Query(None, description="Comma-separated bookmakers (must be allowed in region)"),
):
    """Get odds for multiple events in one request.

    The region parameter is required and determines which bookmakers are available.
    Useful for batch operations to reduce API quota usage.
    Limited to 10 events per request.
    """
    ids_list = [eid.strip() for eid in event_ids.split(",") if eid.strip()]
    if not ids_list:
        raise HTTPException(status_code=400, detail="At least one event ID is required")
    if len(ids_list) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 events per request")

    requested_bm = bookmakers.split(",") if bookmakers else None
    bm_list = get_bookmakers_for_region(region, requested_bm)

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
    region: Region = Query(..., description="Region code (br, fr, uk, es, it, de, mx, ar, co)"),
    bookmaker: str | None = Query(None, description="Filter by specific bookmaker (must be allowed in region)"),
    sport: str | None = None,
    market: str = "ML",
):
    """Get odds that changed since a timestamp.

    The region parameter is required. If a bookmaker is specified, it must be allowed in the region.
    Useful for efficient polling without fetching all odds repeatedly.
    Returns only odds entries that have been modified after the given timestamp.
    """
    if bookmaker:
        validate_bookmaker_access(bookmaker, region)

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
    region: Region = Query(..., description="Region code (br, fr, uk, es, it, de, mx, ar, co)"),
    bookmaker: str | None = Query(None, description="Bookmaker to get movements for (must be allowed in region)"),
    market: str = "ML",
):
    """Get historical odds movements for an event.

    The region parameter is required. Bookmaker must be allowed in the region.
    """
    allowed = get_allowed_bookmakers(region)

    if bookmaker:
        validate_bookmaker_access(bookmaker, region)
        bm = bookmaker
    else:
        # Use first allowed bookmaker for the region
        bm = allowed[0]

    result = await odds_api_provider.get_odds_movements(
        event_id=event_id,
        bookmaker=bm,
        market=market,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="No odds movements found for this event")
    return result
