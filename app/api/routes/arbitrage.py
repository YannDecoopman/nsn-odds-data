from fastapi import APIRouter, Query

from app.providers.odds_api import odds_api_provider
from app.schemas.arbitrage import ArbitrageResponse

router = APIRouter()


@router.get("", response_model=ArbitrageResponse)
async def list_arbitrage_bets(
    sport: str | None = None,
    min_profit: float = Query(
        1.0, alias="minProfit", ge=0, description="Minimum profit margin %"
    ),
    limit: int = Query(5, le=50, description="Max results"),
):
    """List detected arbitrage opportunities across bookmakers."""
    return await odds_api_provider.get_arbitrage_bets(
        sport=sport,
        min_profit=min_profit,
        limit=limit,
    )
