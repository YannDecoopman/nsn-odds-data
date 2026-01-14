from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.providers.odds_api import odds_api_provider
from app.schemas.common import Market
from app.schemas.odds_movements import OddsMovementsResponse

router = APIRouter()


@router.get("")
async def get_odds(
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


@router.get("/movements", response_model=OddsMovementsResponse)
async def get_odds_movements(
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
