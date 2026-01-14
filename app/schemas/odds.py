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


# Both Teams To Score (BTTS) schemas
class BTTSOdds(BaseModel):
    """BTTS odds values."""

    yes: float
    no: float


class BTTSBookmaker(BaseModel):
    """Bookmaker with BTTS odds."""

    key: str
    name: str
    odds: BTTSOdds
    updated_at: datetime


class BTTSOutput(BaseModel):
    """Final JSON output format for BTTS static files."""

    event: EventData
    market: str = "btts"
    bookmakers: list[BTTSBookmaker]
    metadata: OddsMetadata


# Correct Score schemas
class CorrectScoreOdds(BaseModel):
    """Single correct score odds."""

    score: str  # "1-0", "2-1", "Other"
    odds: float


class CorrectScoreBookmaker(BaseModel):
    """Bookmaker with correct score odds."""

    key: str
    name: str
    scores: list[CorrectScoreOdds]
    updated_at: datetime


class CorrectScoreOutput(BaseModel):
    """Final JSON output format for Correct Score static files."""

    event: EventData
    market: str = "correct_score"
    bookmakers: list[CorrectScoreBookmaker]
    metadata: OddsMetadata


# Double Chance schemas
class DoubleChanceOdds(BaseModel):
    """Double chance odds values."""

    home_draw: float  # 1X
    draw_away: float  # X2
    home_away: float  # 12


class DoubleChanceBookmaker(BaseModel):
    """Bookmaker with double chance odds."""

    key: str
    name: str
    odds: DoubleChanceOdds
    updated_at: datetime


class DoubleChanceOutput(BaseModel):
    """Final JSON output format for Double Chance static files."""

    event: EventData
    market: str = "double_chance"
    bookmakers: list[DoubleChanceBookmaker]
    metadata: OddsMetadata
