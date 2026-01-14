from pydantic import BaseModel


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
