from fastapi import APIRouter, Request

from app.config import settings
from app.providers.odds_api import odds_api_provider
from app.schemas.common import SportResponse
from app.services.rate_limiter import limiter

router = APIRouter()


@router.get("", response_model=list[SportResponse])
@limiter.limit(settings.rate_limit_default)
async def list_sports(request: Request):
    """Get available sports from Odds-API.io."""
    sports = await odds_api_provider.get_sports()
    return [
        SportResponse(
            key=s.get("slug", s.get("key", "")),
            title=s.get("name", s.get("title", "")),
            active=s.get("active", True),
        )
        for s in sports
    ]
