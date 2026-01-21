"""Service for managing league whitelist CRUD operations."""

import fnmatch

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LeagueWhitelist


async def get_allowed_leagues(
    session: AsyncSession, sport: str | None = None
) -> set[str]:
    """Get all allowed league slugs, optionally filtered by sport."""
    query = select(LeagueWhitelist.league_slug).where(LeagueWhitelist.is_active == True)
    if sport:
        query = query.where(LeagueWhitelist.sport == sport)
    result = await session.execute(query)
    return set(result.scalars().all())


async def get_allowed_leagues_with_patterns(
    session: AsyncSession, sport: str | None = None
) -> tuple[set[str], list[str]]:
    """Get allowed leagues split into exact matches and patterns (with wildcards)."""
    query = select(LeagueWhitelist.league_slug).where(LeagueWhitelist.is_active == True)
    if sport:
        query = query.where(LeagueWhitelist.sport == sport)
    result = await session.execute(query)
    slugs = result.scalars().all()

    exact = set()
    patterns = []
    for slug in slugs:
        if "*" in slug or "?" in slug:
            patterns.append(slug)
        else:
            exact.add(slug)

    return exact, patterns


def is_league_allowed(
    league_slug: str, exact_matches: set[str], patterns: list[str]
) -> bool:
    """Check if a league slug is allowed (exact match or pattern match)."""
    if league_slug in exact_matches:
        return True
    for pattern in patterns:
        if fnmatch.fnmatch(league_slug, pattern):
            return True
    return False


async def add_league(
    session: AsyncSession,
    sport: str,
    league_slug: str,
    league_name: str | None = None,
) -> LeagueWhitelist:
    """Add a league to the whitelist (upsert)."""
    stmt = (
        insert(LeagueWhitelist)
        .values(
            sport=sport,
            league_slug=league_slug,
            league_name=league_name,
            is_active=True,
        )
        .on_conflict_do_update(
            index_elements=["sport", "league_slug"],
            set_={"league_name": league_name, "is_active": True},
        )
        .returning(LeagueWhitelist)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()


async def remove_league(
    session: AsyncSession, sport: str, league_slug: str
) -> bool:
    """Remove a league from the whitelist."""
    stmt = delete(LeagueWhitelist).where(
        LeagueWhitelist.sport == sport,
        LeagueWhitelist.league_slug == league_slug,
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def toggle_league(
    session: AsyncSession, sport: str, league_slug: str, is_active: bool
) -> bool:
    """Toggle a league's active status."""
    stmt = (
        update(LeagueWhitelist)
        .where(
            LeagueWhitelist.sport == sport,
            LeagueWhitelist.league_slug == league_slug,
        )
        .values(is_active=is_active)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def list_whitelists(
    session: AsyncSession, sport: str | None = None
) -> list[LeagueWhitelist]:
    """List all whitelist entries, optionally filtered by sport."""
    query = select(LeagueWhitelist).order_by(
        LeagueWhitelist.sport, LeagueWhitelist.league_slug
    )
    if sport:
        query = query.where(LeagueWhitelist.sport == sport)
    result = await session.execute(query)
    return list(result.scalars().all())


async def sync_default_whitelist(
    session: AsyncSession, default_whitelist: list[dict]
) -> int:
    """Sync default whitelist entries (insert if not exists)."""
    count = 0
    for entry in default_whitelist:
        stmt = (
            insert(LeagueWhitelist)
            .values(
                sport=entry["sport"],
                league_slug=entry["league_slug"],
                league_name=entry.get("league_name"),
                is_active=True,
            )
            .on_conflict_do_nothing(index_elements=["sport", "league_slug"])
        )
        result = await session.execute(stmt)
        if result.rowcount > 0:
            count += 1
    await session.commit()
    return count
