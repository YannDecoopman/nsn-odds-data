from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from app.schemas.common import LeagueInfo, SportInfo


class EventStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ENDED = "ended"


class ScoreInfo(BaseModel):
    home: int
    away: int


class EventResponse(BaseModel):
    id: str
    home: str
    away: str
    date: datetime
    status: EventStatus = EventStatus.NOT_STARTED
    scores: ScoreInfo | None = None
    sport: SportInfo
    league: LeagueInfo


class LiveEventResponse(EventResponse):
    status: EventStatus = EventStatus.IN_PROGRESS
    minute: int | None = None
    period: str | None = None  # "1H", "2H", "HT"


class PaginationInfo(BaseModel):
    total: int
    limit: int
    offset: int


class EventListResponse(BaseModel):
    data: list[EventResponse]
    pagination: PaginationInfo


class LiveEventsResponse(BaseModel):
    data: list[LiveEventResponse]


class LeagueResponse(BaseModel):
    name: str
    slug: str
    sport: str


class LeaguesResponse(BaseModel):
    data: list[LeagueResponse]
