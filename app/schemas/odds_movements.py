from datetime import datetime

from pydantic import BaseModel, Field


class OddsSnapshot(BaseModel):
    """Single odds snapshot at a point in time."""

    home: float
    draw: float | None = None
    away: float
    timestamp: datetime


class OddsMovementsResponse(BaseModel):
    """Response for odds movements endpoint."""

    event_id: str = Field(alias="eventId")
    bookmaker: str
    market: str
    opening: OddsSnapshot
    latest: OddsSnapshot
    movements: list[OddsSnapshot]

    class Config:
        populate_by_name = True
