from enum import Enum

from pydantic import BaseModel


class Market(str, Enum):
    """Supported betting markets."""

    ML = "1x2"
    ASIAN_HANDICAP = "asian_handicap"
    TOTALS = "totals"
    BTTS = "btts"
    CORRECT_SCORE = "correct_score"
    DOUBLE_CHANCE = "double_chance"


class SportInfo(BaseModel):
    name: str
    slug: str


class LeagueInfo(BaseModel):
    name: str
    slug: str


class SportResponse(BaseModel):
    key: str
    title: str
    active: bool


class BookmakerResponse(BaseModel):
    key: str
    name: str
    region: str | None = None
    is_active: bool = True
