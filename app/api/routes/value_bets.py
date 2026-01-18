from fastapi import APIRouter, Query, Request

from app.config import settings
from app.providers.odds_api import odds_api_provider
from app.schemas.value_bets import ValueBetsResponse
from app.services.rate_limiter import limiter

router = APIRouter()


@router.get("", response_model=ValueBetsResponse)
@limiter.limit(settings.rate_limit_heavy)
async def list_value_bets(
    request: Request,
    sport: str | None = None,
    league: str | None = None,
    min_ev: float = Query(2.0, alias="minEV", ge=0, description="Minimum expected value"),
    limit: int = Query(10, le=50, description="Max results"),
):
    """Get value bets across configured bookmakers.

    Aggregates value bets from multiple bookmakers (bet365, betano, sportingbet, betfair)
    and filters by sport, league, and minimum expected value.
    """
    return await odds_api_provider.get_value_bets(
        sport=sport,
        league=league,
        min_ev=min_ev,
        limit=limit,
    )
