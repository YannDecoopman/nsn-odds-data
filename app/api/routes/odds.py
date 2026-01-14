from fastapi import APIRouter, Query

from app.config import settings
from app.providers.odds_api import odds_api_provider

router = APIRouter()


@router.get("")
async def get_odds(
    event_id: str = Query(..., alias="eventId"),
    market: str = "1x2",
    bookmakers: str | None = None,
):
    """Get odds for an event."""
    bm_list = bookmakers.split(",") if bookmakers else settings.bookmakers_list
    return await odds_api_provider.get_odds(
        event_id=event_id,
        bookmakers=bm_list,
        market=market,
    )
