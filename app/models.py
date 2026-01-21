import uuid
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class RefreshFrequency(str, Enum):
    """How often to refresh odds data based on event proximity."""

    LIVE = "live"  # Every 5 minutes (match today)
    HOURLY = "hourly"  # Every hour (match in 1-5 days)
    DAILY = "daily"  # Once per day (match in 5+ days)
    NONE = "none"  # No refresh (match ended)

    @staticmethod
    def for_event_date(event_date: datetime | None) -> "RefreshFrequency":
        """Calculate refresh frequency based on event date."""
        if event_date is None:
            return RefreshFrequency.HOURLY

        now = datetime.now(event_date.tzinfo) if event_date.tzinfo else datetime.now()
        days_until = (event_date - now).days

        if days_until < 0:
            # Event in the past - check if today
            if event_date.date() == now.date():
                return RefreshFrequency.LIVE
            return RefreshFrequency.NONE
        elif days_until == 0:
            return RefreshFrequency.LIVE
        elif days_until <= 5:
            return RefreshFrequency.HOURLY
        else:
            return RefreshFrequency.DAILY

    def get_interval_seconds(self) -> int:
        """Get refresh interval in seconds."""
        return {
            RefreshFrequency.LIVE: 300,  # 5 minutes
            RefreshFrequency.HOURLY: 3600,  # 1 hour
            RefreshFrequency.DAILY: 86400,  # 24 hours
            RefreshFrequency.NONE: 0,
        }[self]


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
    event_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_refreshed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def needs_refresh(self) -> bool:
        """Check if this request needs to be refreshed based on frequency."""
        if self.is_ended:
            return False

        frequency = RefreshFrequency.for_event_date(self.event_date)
        if frequency == RefreshFrequency.NONE:
            return False

        if self.last_refreshed is None:
            return True

        now = datetime.now(self.last_refreshed.tzinfo) if self.last_refreshed.tzinfo else datetime.now()
        elapsed = (now - self.last_refreshed).total_seconds()
        return elapsed >= frequency.get_interval_seconds()

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


class APIKey(Base):
    """API keys for multi-tenant authentication."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class LeagueWhitelist(Base):
    """Whitelist of allowed leagues per sport."""

    __tablename__ = "league_whitelists"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sport: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    league_slug: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    league_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("uq_sport_league", "sport", "league_slug", unique=True),
    )
