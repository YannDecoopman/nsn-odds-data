from fastapi import APIRouter, Query, Request

from app.config import settings
from app.providers.odds_api import odds_api_provider
from app.schemas.common import Region
from app.schemas.value_bets import ValueBetsResponse
from app.services.rate_limiter import limiter
from app.services.region_filter import get_bookmakers_for_region

router = APIRouter()


@router.get("", response_model=ValueBetsResponse)
@limiter.limit(settings.rate_limit_heavy)
async def list_value_bets(
    request: Request,
    region: Region = Query(..., description="Region code (br, fr, uk, es, it, de, mx, ar, co)"),
    sport: str | None = None,
    league: str | None = None,
    min_ev: float = Query(2.0, alias="minEV", ge=0, description="Minimum expected value"),
    limit: int = Query(10, le=50, description="Max results"),
):
    """Get value bets across bookmakers allowed in the region.

    The region parameter is required and determines which bookmakers are queried.
    Aggregates value bets from the region's allowed bookmakers
    and filters by sport, league, and minimum expected value.
    """
    bookmakers = get_bookmakers_for_region(region)

    return await odds_api_provider.get_value_bets(
        bookmakers=bookmakers,
        sport=sport,
        league=league,
        min_ev=min_ev,
        limit=limit,
    )
