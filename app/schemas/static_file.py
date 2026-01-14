from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    event_id: str
    bookmakers: list[str] | None = None
    market: str = "1x2"


class GenerateResponse(BaseModel):
    request_id: UUID
    status: str
    path: str | None = None


class FileInfoResponse(BaseModel):
    request_id: UUID
    status: str
    path: str | None
    hash: str | None
    updated_at: datetime | None

    class Config:
        from_attributes = True
