import hashlib
import json
from typing import Any

from app.config import settings
from app.providers.base import ProviderInterface
from app.schemas import (
    AsianHandicapOutput,
    EventResponse,
    LiveEventResponse,
    OddsOutput,
    TotalsOutput,
)
from app.services.odds_client import odds_client


class OddsAPIProvider(ProviderInterface):
    """Provider for Odds-API.io data."""

    @staticmethod
    def get_name() -> str:
        return "ODDS_API"

    async def get_sports(self) -> list[dict[str, Any]]:
        return await odds_client.get_sports()

    async def get_events(
        self,
        sport: str | None = None,
        league: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[list[EventResponse], int]:
        return await odds_client.get_events(
            sport=sport,
            league=league,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )

    async def get_live_events(
        self,
        sport: str | None = None,
    ) -> list[LiveEventResponse]:
        return await odds_client.get_live_events(sport=sport)

    async def get_leagues(
        self,
        sport: str | None = None,
    ) -> list[dict[str, Any]]:
        return await odds_client.get_leagues(sport=sport)

    async def get_odds(
        self,
        event_id: str,
        bookmakers: list[str] | None = None,
        market: str = "1x2",
    ) -> OddsOutput | AsianHandicapOutput | TotalsOutput | None:
        if bookmakers is None:
            bookmakers = settings.bookmakers_list

        return await odds_client.get_odds(
            event_id=event_id,
            bookmakers=bookmakers,
            market=market,
        )

    def compute_hash(self, data: dict[str, Any]) -> str:
        """Compute MD5 hash of odds data for change detection."""
        # Only hash the relevant changing parts (odds values)
        hash_content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(hash_content.encode()).hexdigest()


odds_api_provider = OddsAPIProvider()
