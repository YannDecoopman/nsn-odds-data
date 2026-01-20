from enum import Enum

from pydantic import BaseModel, ConfigDict


class Region(str, Enum):
    """Supported betting regions (country codes)."""

    BR = "br"  # Brazil
    FR = "fr"  # France
    UK = "uk"  # United Kingdom
    ES = "es"  # Spain
    IT = "it"  # Italy
    DE = "de"  # Germany
    MX = "mx"  # Mexico
    AR = "ar"  # Argentina
    CO = "co"  # Colombia


class Market(str, Enum):
    """Supported betting markets."""

    ML = "1x2"
    ASIAN_HANDICAP = "asian_handicap"
    TOTALS = "totals"
    BTTS = "btts"
    CORRECT_SCORE = "correct_score"
    DOUBLE_CHANCE = "double_chance"


class CamelCaseModel(BaseModel):
    """Base model with camelCase alias support."""

    model_config = ConfigDict(populate_by_name=True)


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
