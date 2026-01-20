from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Region


class GenerateRequest(BaseModel):
    event_id: str
    region: Region
    bookmakers: list[str] | None = None
    market: str = "1x2"


class GenerateResponse(BaseModel):
    request_id: UUID
    status: str
    path: str | None = None


class FileInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: UUID
    status: str
    path: str | None
    hash: str | None
    updated_at: datetime | None
