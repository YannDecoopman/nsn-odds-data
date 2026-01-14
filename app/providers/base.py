from abc import ABC, abstractmethod
from typing import Any

from app.schemas import EventResponse, OddsOutput


class ProviderInterface(ABC):
    """Interface for data providers (inspired by BlockProviderInterface)."""

    @staticmethod
    @abstractmethod
    def get_name() -> str:
        """Provider identifier (e.g., 'ODDS_API')."""
        ...

    @abstractmethod
    async def get_sports(self) -> list[dict[str, Any]]:
        """Get available sports."""
        ...

    @abstractmethod
    async def get_events(
        self,
        sport: str = "football",
        date: str | None = None,
    ) -> list[EventResponse]:
        """Get events for a sport."""
        ...

    @abstractmethod
    async def get_odds(
        self,
        event_id: str,
        bookmakers: list[str],
        market: str = "1x2",
    ) -> OddsOutput | None:
        """Get odds for an event."""
        ...

    @abstractmethod
    def compute_hash(self, data: dict[str, Any]) -> str:
        """Compute hash for change detection."""
        ...
