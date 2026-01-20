from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import CamelCaseModel, LeagueInfo, SportInfo


class ValueBetOdds(CamelCaseModel):
    """Bookmaker odds for a value bet."""

    home: float
    draw: float | None = None  # None for 2-way markets (tennis, etc.)
    away: float
    home_direct_link: str | None = Field(None, alias="homeDirectLink")


class ConsensusOdds(BaseModel):
    """Market consensus odds (sharp bookmakers average)."""

    home: float
    draw: float | None = None
    away: float


class ValueBetEvent(BaseModel):
    """Event info embedded in value bet response."""

    home: str
    away: str
    date: datetime
    sport: SportInfo
    league: LeagueInfo


class ValueBet(CamelCaseModel):
    """Single value bet opportunity."""

    id: str
    event_id: str = Field(alias="eventId")
    bookmaker: str
    market: str
    bet_side: str = Field(alias="betSide")
    expected_value: float = Field(alias="expectedValue")
    expected_value_updated_at: datetime = Field(alias="expectedValueUpdatedAt")
    bookmaker_odds: ValueBetOdds = Field(alias="bookmakerOdds")
    consensus_odds: ConsensusOdds = Field(alias="consensusOdds")
    event: ValueBetEvent


class ValueBetsResponse(BaseModel):
    """Response wrapper for value bets list."""

    data: list[ValueBet]
