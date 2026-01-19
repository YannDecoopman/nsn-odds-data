from pydantic import BaseModel


class ParticipantResponse(BaseModel):
    id: str
    name: str
    slug: str
    sport: str
    country: str | None = None
    logo: str | None = None


class ParticipantsListResponse(BaseModel):
    data: list[ParticipantResponse]
    total: int
