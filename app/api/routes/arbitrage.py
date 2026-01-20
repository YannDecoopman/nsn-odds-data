from fastapi import APIRouter, Query, Request

from app.config import settings
from app.providers.odds_api import odds_api_provider
from app.schemas.arbitrage import ArbitrageResponse
from app.schemas.common import Region
from app.services.rate_limiter import limiter
from app.services.region_filter import get_bookmakers_for_region

router = APIRouter()


@router.get("", response_model=ArbitrageResponse)
@limiter.limit(settings.rate_limit_heavy)
async def list_arbitrage_bets(
    request: Request,
    region: Region = Query(..., description="Region code (br, fr, uk, es, it, de, mx, ar, co)"),
    sport: str | None = None,
    min_profit: float = Query(
        1.0, alias="minProfit", ge=0, description="Minimum profit margin %"
    ),
    limit: int = Query(5, le=50, description="Max results"),
):
    """List detected arbitrage opportunities across bookmakers allowed in the region.

    The region parameter is required and determines which bookmakers are queried.
    """
    bookmakers = get_bookmakers_for_region(region)

    return await odds_api_provider.get_arbitrage_bets(
        bookmakers=bookmakers,
        sport=sport,
        min_profit=min_profit,
        limit=limit,
    )
