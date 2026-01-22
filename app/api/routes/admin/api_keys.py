"""Admin endpoint for managing API keys."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.config import settings
from app.db import async_session_maker
from app.services import api_key_service

router = APIRouter(prefix="/admin/api-keys", tags=["admin"])


class CreateKeyRequest(BaseModel):
    name: str


class CreateKeyResponse(BaseModel):
    key: str
    name: str
    message: str


class KeyInfo(BaseModel):
    id: int
    name: str
    key_preview: str
    is_active: bool
    created_at: str | None
    last_used_at: str | None


def verify_admin_token(x_admin_token: str | None = Header(None)) -> None:
    """Verify admin token is present and valid."""
    if not settings.admin_token:
        raise HTTPException(status_code=503, detail="Admin endpoint not configured")
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.post("", response_model=CreateKeyResponse)
async def create_api_key(
    request: CreateKeyRequest,
    x_admin_token: str | None = Header(None),
):
    """Create a new API key."""
    verify_admin_token(x_admin_token)

    async with async_session_maker() as session:
        api_key = await api_key_service.create_key(session, request.name)
        return CreateKeyResponse(
            key=api_key.key,
            name=api_key.name,
            message="API key created successfully. Store this key securely.",
        )


@router.get("", response_model=list[KeyInfo])
async def list_api_keys(x_admin_token: str | None = Header(None)):
    """List all API keys."""
    verify_admin_token(x_admin_token)

    async with async_session_maker() as session:
        keys = await api_key_service.list_keys(session)
        return [
            KeyInfo(
                id=key.id,
                name=key.name,
                key_preview=f"{key.key[:12]}...{key.key[-4:]}" if len(key.key) > 16 else key.key,
                is_active=key.is_active,
                created_at=key.created_at.isoformat() if key.created_at else None,
                last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
            )
            for key in keys
        ]


@router.delete("/{key}")
async def revoke_api_key(key: str, x_admin_token: str | None = Header(None)):
    """Revoke an API key."""
    verify_admin_token(x_admin_token)

    async with async_session_maker() as session:
        success = await api_key_service.revoke_key(session, key)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found")
        return {"message": "API key revoked successfully"}
