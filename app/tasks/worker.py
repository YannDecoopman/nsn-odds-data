import logging
from uuid import UUID

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from app.api.routes.events import _fetch_upcoming_events
from app.config import settings
from app.db import async_session_maker
from app.models import RequestData, StaticFile
from app.services.cache import CACHE_KEY_UPCOMING, cache_service
from app.services.static_file import static_file_service

logger = logging.getLogger(__name__)


async def generate_static_file_task(ctx: dict, static_file_id: UUID, bookmakers: list[str] | None = None) -> bool:
    """Background task to generate static file."""
    async with async_session_maker() as db:
        stmt = select(StaticFile).where(StaticFile.id == static_file_id)
        result = await db.execute(stmt)
        static_file = result.scalar_one_or_none()

        if not static_file:
            logger.error(f"StaticFile not found: {static_file_id}")
            return False

        # Load relationship
        stmt = select(RequestData).where(RequestData.id == static_file.request_data_id)
        result = await db.execute(stmt)
        static_file.request_data = result.scalar_one()

        success = await static_file_service.generate_static_file(
            db=db,
            static_file=static_file,
            bookmakers=bookmakers,
        )
        await db.commit()
        return success


async def refresh_active_odds(ctx: dict) -> dict:
    """Scheduled task to refresh odds files based on intelligent frequency.

    Frequency is determined by event date:
    - LIVE (today): refresh every 5 minutes
    - HOURLY (1-5 days away): refresh every hour
    - DAILY (5+ days away): refresh once per day
    - NONE (ended): no refresh
    """
    logger.info("Starting intelligent odds refresh job")

    async with async_session_maker() as db:
        # Get all active request_data
        stmt = select(RequestData).where(RequestData.is_ended == False)
        result = await db.execute(stmt)
        active_requests = result.scalars().all()

        refreshed_count = 0
        skipped_count = 0
        error_count = 0

        for request_data in active_requests:
            # Check if refresh is needed based on frequency
            if not request_data.needs_refresh():
                skipped_count += 1
                continue

            # Get static file
            stmt = select(StaticFile).where(StaticFile.request_data_id == request_data.id)
            result = await db.execute(stmt)
            static_file = result.scalar_one_or_none()

            if not static_file:
                continue

            static_file.request_data = request_data

            try:
                success = await static_file_service.generate_static_file(
                    db=db,
                    static_file=static_file,
                )
                if success:
                    # Update last_refreshed timestamp
                    from datetime import datetime
                    request_data.last_refreshed = datetime.now()
                    refreshed_count += 1
            except Exception as e:
                logger.error(f"Failed to refresh {request_data.provider_id}: {e}")
                error_count += 1

        await db.commit()

    logger.info(
        f"Odds refresh completed: {refreshed_count} refreshed, "
        f"{skipped_count} skipped (not due), {error_count} errors"
    )
    return {"refreshed": refreshed_count, "skipped": skipped_count, "errors": error_count}


async def refresh_upcoming_events(ctx: dict) -> dict:
    """Scheduled task to refresh upcoming events cache for major leagues."""
    logger.info("Starting upcoming events refresh job")

    try:
        events = await _fetch_upcoming_events()

        await cache_service.set(
            CACHE_KEY_UPCOMING,
            [e.model_dump(mode="json") for e in events],
            ttl=settings.cache_ttl_upcoming,
        )

        logger.info(f"Upcoming events refresh completed: {len(events)} events cached")
        return {"cached": len(events)}

    except Exception as e:
        logger.error(f"Failed to refresh upcoming events: {e}")
        return {"error": str(e)}


class WorkerSettings:
    """ARQ worker settings."""

    functions = [generate_static_file_task]
    cron_jobs = [
        # Intelligent refresh: runs every 5 min but only refreshes what's due
        # - LIVE events (today): refreshed every 5 min
        # - HOURLY events (1-5 days): refreshed every hour
        # - DAILY events (5+ days): refreshed once per day
        cron(refresh_active_odds, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
        # Refresh upcoming events cache (offset by 2 min to avoid overlap)
        cron(refresh_upcoming_events, minute={2}),
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 300  # 5 minutes
