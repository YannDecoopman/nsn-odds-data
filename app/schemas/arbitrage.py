from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import CamelCaseModel, LeagueInfo, SportInfo


class ArbitrageLeg(CamelCaseModel):
    """Individual leg of an arbitrage opportunity."""

    side: str
    bookmaker: str
    odds: float
    direct_link: str | None = Field(None, alias="directLink")


class OptimalStake(CamelCaseModel):
    """Optimal stake for a leg."""

    side: str
    bookmaker: str
    stake: float
    potential_return: float = Field(alias="potentialReturn")


class ArbitrageEvent(BaseModel):
    """Event info for arbitrage opportunity."""

    home: str
    away: str
    date: datetime
    sport: SportInfo
    league: LeagueInfo


class ArbitrageBet(CamelCaseModel):
    """Single arbitrage opportunity."""

    id: str
    event_id: str = Field(alias="eventId")
    market: str
    profit_margin: float = Field(alias="profitMargin")
    implied_probability: float = Field(alias="impliedProbability")
    total_stake: float = Field(alias="totalStake")
    legs: list[ArbitrageLeg]
    optimal_stakes: list[OptimalStake] = Field(alias="optimalStakes")
    event: ArbitrageEvent
    detected_at: datetime = Field(alias="detectedAt")


class ArbitrageResponse(BaseModel):
    """Response for arbitrage bets endpoint."""

    data: list[ArbitrageBet]
