from fastapi import APIRouter

from app.providers.odds_api import odds_api_provider
from app.schemas.events import LeagueResponse, LeaguesResponse

router = APIRouter()


@router.get("", response_model=LeaguesResponse)
async def list_leagues(sport: str | None = None):
    """Get available leagues."""
    leagues = await odds_api_provider.get_leagues(sport=sport)
    return LeaguesResponse(
        data=[
            LeagueResponse(
                name=league.get("name", ""),
                slug=league.get("slug", ""),
                sport=league.get("sport", sport or "football"),
            )
            for league in leagues
        ]
    )
