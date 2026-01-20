import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import RequestData, StaticFile
from app.providers.odds_api import odds_api_provider
from app.schemas import OddsOutput

logger = logging.getLogger(__name__)


class StaticFileService:
    """Service for generating and managing static JSON files."""

    def __init__(self):
        self.provider = odds_api_provider
        self.static_path = Path(settings.static_files_path)
        self.static_path.mkdir(parents=True, exist_ok=True)

    async def get_or_create_request_data(
        self,
        db: AsyncSession,
        event_id: str,
        market: str = "1x2",
    ) -> RequestData:
        """Get existing or create new RequestData record."""
        provider_name = self.provider.get_name()

        # Check if exists
        stmt = select(RequestData).where(
            RequestData.provider == provider_name,
            RequestData.provider_id == event_id,
            RequestData.market == market,
        )
        result = await db.execute(stmt)
        request_data = result.scalar_one_or_none()

        if request_data:
            return request_data

        # Create new
        request_data = RequestData(
            provider=provider_name,
            provider_id=event_id,
            sport="football",
            market=market,
        )
        db.add(request_data)
        await db.flush()
        return request_data

    async def get_or_create_static_file(
        self,
        db: AsyncSession,
        request_data: RequestData,
    ) -> StaticFile:
        """Get existing or create new StaticFile record."""
        # Check if exists
        stmt = select(StaticFile).where(StaticFile.request_data_id == request_data.id)
        result = await db.execute(stmt)
        static_file = result.scalar_one_or_none()

        if static_file:
            return static_file

        # Generate path
        now = datetime.now()
        file_name = f"odds-{request_data.provider_id}-{uuid.uuid4().hex[:8]}.json"
        relative_path = f"{now.year}/{now.month:02d}/{file_name}"

        static_file = StaticFile(
            request_data_id=request_data.id,
            path=relative_path,
        )
        db.add(static_file)
        await db.flush()
        return static_file

    async def generate_static_file(
        self,
        db: AsyncSession,
        static_file: StaticFile,
        bookmakers: list[str] | None = None,
        force: bool = False,
    ) -> bool:
        """
        Generate static JSON file with hash-based change detection.
        Returns True if file was generated/updated, False otherwise.
        """
        request_data = static_file.request_data

        # Fetch odds from provider
        odds_data = await self.provider.get_odds(
            event_id=request_data.provider_id,
            bookmakers=bookmakers,
            market=request_data.market,
        )

        if not odds_data:
            logger.warning(f"No odds data for event {request_data.provider_id}")
            return False

        # Compute hash
        data_dict = odds_data.model_dump(mode="json")
        new_hash = self.provider.compute_hash(data_dict)

        # Check if changed (unless force)
        if not force and static_file.hash == new_hash:
            logger.debug(f"No changes for {static_file.path}")
            return False

        # Build output in NSN format
        last_modified = int(datetime.now().timestamp())
        output = {
            "lastModified": last_modified,
            "data": {
                "event": odds_data.event.model_dump(mode="json"),
                "market": odds_data.market,
                "bookmakers": [bm.model_dump(mode="json") for bm in odds_data.bookmakers],
            },
            "isEnded": odds_data.metadata.is_ended,
            "hash": new_hash,
        }

        # Write to file
        full_path = self.static_path / static_file.path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)

        # Update database
        static_file.hash = new_hash
        static_file.last_modified = last_modified

        # Update event_date from odds data (for intelligent refresh frequency)
        if hasattr(odds_data, 'event') and hasattr(odds_data.event, 'commence_time'):
            request_data.event_date = odds_data.event.commence_time

        # Check if event ended
        if odds_data.metadata.is_ended:
            request_data.is_ended = True

        logger.info(f"Generated static file: {static_file.path}")
        return True

    async def get_static_file_by_request_id(
        self,
        db: AsyncSession,
        request_id: uuid.UUID,
    ) -> StaticFile | None:
        """Get static file by request_data ID."""
        stmt = select(StaticFile).where(StaticFile.request_data_id == request_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    def get_file_content(self, path: str) -> dict[str, Any] | None:
        """Read static file content."""
        full_path = self.static_path / path
        if not full_path.exists():
            return None

        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def clean_ended_events(
        self,
        db: AsyncSession,
        retention_days: int | None = None,
    ) -> dict[str, int]:
        """Remove ended events older than retention period.

        Returns dict with counts of deleted items.
        """
        if retention_days is None:
            retention_days = settings.retention_days_ended

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_files = 0
        deleted_requests = 0

        # Find ended RequestData older than cutoff
        stmt = select(RequestData).where(
            RequestData.is_ended == True,
            RequestData.updated_at < cutoff_date,
        )
        result = await db.execute(stmt)
        old_requests = result.scalars().all()

        for request_data in old_requests:
            # Get associated static files
            stmt = select(StaticFile).where(StaticFile.request_data_id == request_data.id)
            result = await db.execute(stmt)
            static_files = result.scalars().all()

            # Delete files from disk
            for sf in static_files:
                full_path = self.static_path / sf.path
                if full_path.exists():
                    try:
                        full_path.unlink()
                        deleted_files += 1
                        logger.debug(f"Deleted file: {sf.path}")
                    except OSError as e:
                        logger.warning(f"Failed to delete {sf.path}: {e}")

            # Delete from DB (cascade will handle static_files)
            await db.delete(request_data)
            deleted_requests += 1

        await db.flush()

        logger.info(
            f"Cleaned ended events: {deleted_requests} requests, {deleted_files} files"
        )
        return {"deleted_requests": deleted_requests, "deleted_files": deleted_files}

    async def clean_orphan_files(self, db: AsyncSession) -> dict[str, int]:
        """Remove files on disk that don't exist in DB."""
        deleted_files = 0

        # Get all paths from DB
        stmt = select(StaticFile.path)
        result = await db.execute(stmt)
        db_paths = set(row[0] for row in result.all())

        # Scan static directory
        for file_path in self.static_path.rglob("*.json"):
            relative_path = str(file_path.relative_to(self.static_path))
            if relative_path not in db_paths:
                try:
                    file_path.unlink()
                    deleted_files += 1
                    logger.debug(f"Deleted orphan file: {relative_path}")
                except OSError as e:
                    logger.warning(f"Failed to delete orphan {relative_path}: {e}")

        logger.info(f"Cleaned orphan files: {deleted_files}")
        return {"deleted_orphan_files": deleted_files}

    async def clean_empty_directories(self) -> dict[str, int]:
        """Remove empty directories in static path."""
        deleted_dirs = 0

        # Walk bottom-up to delete empty dirs
        for dir_path in sorted(self.static_path.rglob("*"), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                try:
                    dir_path.rmdir()
                    deleted_dirs += 1
                    logger.debug(f"Deleted empty dir: {dir_path}")
                except OSError:
                    pass

        logger.info(f"Cleaned empty directories: {deleted_dirs}")
        return {"deleted_directories": deleted_dirs}

    async def clean_all(
        self,
        db: AsyncSession,
        retention_days: int | None = None,
    ) -> dict[str, int]:
        """Run all cleanup tasks."""
        results = {}

        # Clean ended events
        ended_result = await self.clean_ended_events(db, retention_days)
        results.update(ended_result)

        # Clean orphan files
        orphan_result = await self.clean_orphan_files(db)
        results.update(orphan_result)

        # Clean empty directories
        dirs_result = await self.clean_empty_directories()
        results.update(dirs_result)

        return results


static_file_service = StaticFileService()
