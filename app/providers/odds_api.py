import hashlib
import json
from typing import Any

from app.config import settings
from app.providers.base import ProviderInterface
from app.schemas import (
    AsianHandicapOutput,
    BTTSOutput,
    CorrectScoreOutput,
    DoubleChanceOutput,
    EventResponse,
    LiveEventResponse,
    OddsOutput,
    TotalsOutput,
)
from app.schemas.arbitrage import ArbitrageResponse
from app.schemas.odds_movements import OddsMovementsResponse
from app.schemas.value_bets import ValueBetsResponse
from app.services.odds_client import odds_client


class OddsAPIProvider(ProviderInterface):
    """Provider for Odds-API.io data."""

    @staticmethod
    def get_name() -> str:
        return "ODDS_API"

    async def get_sports(self) -> list[dict[str, Any]]:
        return await odds_client.get_sports()

    async def get_bookmakers(self) -> list[dict[str, Any]]:
        return await odds_client.get_bookmakers()

    async def get_event(self, event_id: str) -> EventResponse | None:
        return await odds_client.get_event(event_id)

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
    ) -> OddsOutput | AsianHandicapOutput | TotalsOutput | BTTSOutput | CorrectScoreOutput | DoubleChanceOutput | None:
        if bookmakers is None:
            bookmakers = settings.bookmakers_list

        return await odds_client.get_odds(
            event_id=event_id,
            bookmakers=bookmakers,
            market=market,
        )

    async def get_value_bets(
        self,
        bookmakers: list[str] | None = None,
        sport: str | None = None,
        league: str | None = None,
        min_ev: float = 2.0,
        limit: int = 10,
    ) -> ValueBetsResponse:
        """Get value bets from specified bookmakers."""
        bm_list = bookmakers if bookmakers else settings.bookmakers_list
        return await odds_client.get_value_bets(
            bookmakers=bm_list,
            sport=sport,
            league=league,
            min_ev=min_ev,
            limit=limit,
        )

    async def get_arbitrage_bets(
        self,
        bookmakers: list[str] | None = None,
        sport: str | None = None,
        min_profit: float = 1.0,
        limit: int = 5,
    ) -> ArbitrageResponse:
        """Get arbitrage opportunities from specified bookmakers."""
        bm_list = bookmakers if bookmakers else settings.bookmakers_list
        return await odds_client.get_arbitrage_bets(
            bookmakers=bm_list,
            sport=sport,
            min_profit=min_profit,
            limit=limit,
        )

    async def get_odds_movements(
        self,
        event_id: str,
        bookmaker: str,
        market: str = "ML",
    ) -> OddsMovementsResponse | None:
        """Get historical odds movements for an event."""
        return await odds_client.get_odds_movements(
            event_id=event_id,
            bookmaker=bookmaker,
            market=market,
        )

    async def get_odds_multi(
        self,
        event_ids: list[str],
        bookmakers: list[str] | None = None,
        market: str = "1x2",
    ) -> list[OddsOutput | AsianHandicapOutput | TotalsOutput | BTTSOutput | CorrectScoreOutput | DoubleChanceOutput]:
        """Get odds for multiple events in one request."""
        if bookmakers is None:
            bookmakers = settings.bookmakers_list
        return await odds_client.get_odds_multi(
            event_ids=event_ids,
            bookmakers=bookmakers,
            market=market,
        )

    async def get_odds_updated(
        self,
        since: int,
        bookmaker: str | None = None,
        sport: str | None = None,
        market: str = "ML",
    ) -> list[dict[str, Any]]:
        """Get odds that changed since a timestamp."""
        return await odds_client.get_odds_updated(
            since=since,
            bookmaker=bookmaker,
            sport=sport,
            market=market,
        )

    async def get_participants(
        self,
        sport: str,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get participants/teams for a sport."""
        return await odds_client.get_participants(sport=sport, search=search)

    async def get_participant(self, participant_id: str) -> dict[str, Any] | None:
        """Get a single participant by ID."""
        return await odds_client.get_participant(participant_id)

    def compute_hash(self, data: dict[str, Any]) -> str:
        """Compute MD5 hash of odds data for change detection."""
        # Only hash the relevant changing parts (odds values)
        hash_content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(hash_content.encode()).hexdigest()


odds_api_provider = OddsAPIProvider()
