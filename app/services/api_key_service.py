"""API Key service for multi-tenant authentication."""

import secrets
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import APIKey


def generate_api_key() -> str:
    """Generate a secure API key with nsn_ prefix."""
    return f"nsn_{secrets.token_urlsafe(32)}"


async def validate_key(session: AsyncSession, key: str) -> APIKey | None:
    """Validate an API key and return the record if valid and active."""
    result = await session.execute(
        select(APIKey).where(APIKey.key == key, APIKey.is_active == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def touch_key(session: AsyncSession, key_id: int) -> None:
    """Update last_used_at timestamp for an API key."""
    await session.execute(
        update(APIKey)
        .where(APIKey.id == key_id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await session.commit()


async def create_key(session: AsyncSession, name: str) -> APIKey:
    """Create a new API key for a site."""
    api_key = APIKey(
        key=generate_api_key(),
        name=name,
        is_active=True,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return api_key


async def list_keys(session: AsyncSession) -> list[APIKey]:
    """List all API keys."""
    result = await session.execute(select(APIKey).order_by(APIKey.created_at.desc()))
    return list(result.scalars().all())


async def get_key_by_name(session: AsyncSession, name: str) -> APIKey | None:
    """Get an API key by site name."""
    result = await session.execute(select(APIKey).where(APIKey.name == name))
    return result.scalar_one_or_none()


async def revoke_key(session: AsyncSession, key: str) -> bool:
    """Revoke an API key (set is_active=False)."""
    result = await session.execute(
        update(APIKey).where(APIKey.key == key).values(is_active=False)
    )
    await session.commit()
    return result.rowcount > 0


async def delete_key(session: AsyncSession, key: str) -> bool:
    """Permanently delete an API key."""
    api_key = await session.execute(select(APIKey).where(APIKey.key == key))
    record = api_key.scalar_one_or_none()
    if record:
        await session.delete(record)
        await session.commit()
        return True
    return False
