from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import LeagueInfo, SportInfo


class ArbitrageLeg(BaseModel):
    """Individual leg of an arbitrage opportunity."""

    side: str
    bookmaker: str
    odds: float
    direct_link: str | None = Field(None, alias="directLink")

    class Config:
        populate_by_name = True


class OptimalStake(BaseModel):
    """Optimal stake for a leg."""

    side: str
    bookmaker: str
    stake: float
    potential_return: float = Field(alias="potentialReturn")

    class Config:
        populate_by_name = True


class ArbitrageEvent(BaseModel):
    """Event info for arbitrage opportunity."""

    home: str
    away: str
    date: datetime
    sport: SportInfo
    league: LeagueInfo


class ArbitrageBet(BaseModel):
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

    class Config:
        populate_by_name = True


class ArbitrageResponse(BaseModel):
    """Response for arbitrage bets endpoint."""

    data: list[ArbitrageBet]
