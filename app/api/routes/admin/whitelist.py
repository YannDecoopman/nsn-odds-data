"""Admin endpoints for managing league whitelist."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.data.default_whitelist import DEFAULT_WHITELIST
from app.db import async_session_maker
from app.services import league_whitelist_service

router = APIRouter()


class WhitelistEntry(BaseModel):
    id: int
    sport: str
    league_slug: str
    league_name: str | None
    is_active: bool


class WhitelistCreateRequest(BaseModel):
    sport: str
    league_slug: str
    league_name: str | None = None


class WhitelistToggleRequest(BaseModel):
    is_active: bool


class WhitelistListResponse(BaseModel):
    data: list[WhitelistEntry]
    count: int


class SyncResponse(BaseModel):
    added: int
    message: str


@router.get("", response_model=WhitelistListResponse)
async def list_whitelists(
    sport: str | None = Query(None, description="Filter by sport"),
):
    """List all whitelist entries, optionally filtered by sport."""
    async with async_session_maker() as session:
        entries = await league_whitelist_service.list_whitelists(session, sport)
        data = [
            WhitelistEntry(
                id=e.id,
                sport=e.sport,
                league_slug=e.league_slug,
                league_name=e.league_name,
                is_active=e.is_active,
            )
            for e in entries
        ]
        return WhitelistListResponse(data=data, count=len(data))


@router.get("/{sport}", response_model=WhitelistListResponse)
async def list_whitelists_by_sport(sport: str):
    """List whitelist entries for a specific sport."""
    async with async_session_maker() as session:
        entries = await league_whitelist_service.list_whitelists(session, sport)
        data = [
            WhitelistEntry(
                id=e.id,
                sport=e.sport,
                league_slug=e.league_slug,
                league_name=e.league_name,
                is_active=e.is_active,
            )
            for e in entries
        ]
        return WhitelistListResponse(data=data, count=len(data))


@router.post("", response_model=WhitelistEntry)
async def add_whitelist_entry(request: WhitelistCreateRequest):
    """Add a league to the whitelist."""
    async with async_session_maker() as session:
        entry = await league_whitelist_service.add_league(
            session,
            sport=request.sport,
            league_slug=request.league_slug,
            league_name=request.league_name,
        )
        return WhitelistEntry(
            id=entry.id,
            sport=entry.sport,
            league_slug=entry.league_slug,
            league_name=entry.league_name,
            is_active=entry.is_active,
        )


@router.delete("/{sport}/{league_slug:path}")
async def remove_whitelist_entry(sport: str, league_slug: str):
    """Remove a league from the whitelist."""
    async with async_session_maker() as session:
        removed = await league_whitelist_service.remove_league(
            session, sport, league_slug
        )
        if not removed:
            raise HTTPException(status_code=404, detail="Whitelist entry not found")
        return {"status": "deleted", "sport": sport, "league_slug": league_slug}


@router.patch("/{sport}/{league_slug:path}")
async def toggle_whitelist_entry(
    sport: str, league_slug: str, request: WhitelistToggleRequest
):
    """Toggle a league's active status."""
    async with async_session_maker() as session:
        updated = await league_whitelist_service.toggle_league(
            session, sport, league_slug, request.is_active
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Whitelist entry not found")
        return {
            "status": "updated",
            "sport": sport,
            "league_slug": league_slug,
            "is_active": request.is_active,
        }


@router.post("/sync", response_model=SyncResponse)
async def sync_default_whitelist():
    """Sync default whitelist entries (insert missing ones)."""
    async with async_session_maker() as session:
        added = await league_whitelist_service.sync_default_whitelist(
            session, DEFAULT_WHITELIST
        )
        return SyncResponse(
            added=added,
            message=f"Added {added} new entries from default whitelist",
        )
