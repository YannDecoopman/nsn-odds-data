import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RequestData(Base):
    """Tracks unique data requests by provider type + ID."""

    __tablename__ = "request_data"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sport: Mapped[str] = mapped_column(String(50), default="football")
    market: Mapped[str] = mapped_column(String(50), default="1x2")
    is_ended: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    static_files: Mapped[list["StaticFile"]] = relationship(
        "StaticFile", back_populates="request_data", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_request_provider", "provider", "provider_id", "market", unique=True),
    )


class StaticFile(Base):
    """Generated static JSON files."""

    __tablename__ = "static_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("request_data.id", ondelete="CASCADE"), nullable=False
    )
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_modified: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    request_data: Mapped["RequestData"] = relationship(
        "RequestData", back_populates="static_files"
    )

    __table_args__ = (
        Index("idx_static_path", "path"),
        Index("idx_static_request", "request_data_id"),
    )
