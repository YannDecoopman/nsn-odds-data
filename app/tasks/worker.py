import logging
from uuid import UUID

from arq import cron
from arq.connections import RedisSettings

from app.config import settings
from app.db import async_session_maker
from app.models import RequestData, StaticFile
from app.services.static_file import static_file_service
from sqlalchemy import select

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
    """Scheduled task to refresh all active (non-ended) odds files."""
    logger.info("Starting odds refresh job")

    async with async_session_maker() as db:
        # Get all active request_data
        stmt = select(RequestData).where(RequestData.is_ended == False)
        result = await db.execute(stmt)
        active_requests = result.scalars().all()

        success_count = 0
        error_count = 0

        for request_data in active_requests:
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
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed to refresh {request_data.provider_id}: {e}")
                error_count += 1

        await db.commit()

    logger.info(f"Odds refresh completed: {success_count} success, {error_count} errors")
    return {"success": success_count, "errors": error_count}


class WorkerSettings:
    """ARQ worker settings."""

    functions = [generate_static_file_task]
    cron_jobs = [
        cron(refresh_active_odds, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),  # Every 5 minutes
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 300  # 5 minutes
