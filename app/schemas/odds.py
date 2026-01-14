from datetime import datetime

from pydantic import BaseModel


class EventData(BaseModel):
    id: str
    sport: str
    league: str | None = None
    league_id: str | None = None
    home_team: str
    away_team: str
    commence_time: datetime


class OddsValues(BaseModel):
    home: float
    draw: float
    away: float


class BookmakerOdds(BaseModel):
    key: str
    name: str
    odds: OddsValues
    updated_at: datetime


class OddsMetadata(BaseModel):
    generated_at: datetime
    is_ended: bool = False
    hash: str


class OddsOutput(BaseModel):
    """Final JSON output format for static files."""

    event: EventData
    market: str = "1x2"
    bookmakers: list[BookmakerOdds]
    metadata: OddsMetadata


# Asian Handicap schemas
class AsianHandicapLine(BaseModel):
    """Single handicap line with odds."""

    hdp: float  # -0.5, -1.0, -1.5, +0.5, etc.
    home: float
    away: float


class AsianHandicapBookmaker(BaseModel):
    """Bookmaker with multiple handicap lines."""

    key: str
    name: str
    lines: list[AsianHandicapLine]
    updated_at: datetime


class AsianHandicapOutput(BaseModel):
    """Final JSON output format for Asian Handicap static files."""

    event: EventData
    market: str = "asian_handicap"
    bookmakers: list[AsianHandicapBookmaker]
    metadata: OddsMetadata


# Totals (Over/Under) schemas
class TotalsLine(BaseModel):
    """Single totals line with odds."""

    line: float  # 2.5, 3.5, etc.
    over: float
    under: float


class TotalsBookmaker(BaseModel):
    """Bookmaker with multiple totals lines."""

    key: str
    name: str
    lines: list[TotalsLine]
    updated_at: datetime


class TotalsOutput(BaseModel):
    """Final JSON output format for Totals (Over/Under) static files."""

    event: EventData
    market: str = "totals"
    bookmakers: list[TotalsBookmaker]
    metadata: OddsMetadata
