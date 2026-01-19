from fastapi import APIRouter, Request

from app.config import settings
from app.providers.odds_api import odds_api_provider
from app.schemas.common import BookmakerResponse
from app.services.rate_limiter import limiter

router = APIRouter()


@router.get("", response_model=list[BookmakerResponse])
@limiter.limit(settings.rate_limit_default)
async def list_bookmakers(request: Request):
    """Get available bookmakers from Odds-API.io."""
    bookmakers = await odds_api_provider.get_bookmakers()
    return [
        BookmakerResponse(
            key=b.get("key", b.get("slug", "")),
            name=b.get("name", b.get("title", "")),
            region=b.get("region"),
            is_active=b.get("isActive", b.get("active", True)),
        )
        for b in bookmakers
    ]
