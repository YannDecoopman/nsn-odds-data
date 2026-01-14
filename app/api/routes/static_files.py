from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.config import settings
from app.schemas.static_file import FileInfoResponse, GenerateRequest, GenerateResponse
from app.services.static_file import static_file_service

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate_odds_file(
    request: GenerateRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Request generation of a static odds file."""
    request_data = await static_file_service.get_or_create_request_data(
        db=db,
        event_id=request.event_id,
        market=request.market,
    )
    static_file = await static_file_service.get_or_create_static_file(
        db=db,
        request_data=request_data,
    )
    await db.commit()

    bookmakers = request.bookmakers or settings.bookmakers_list

    if req.app.state.arq_pool:
        await req.app.state.arq_pool.enqueue_job(
            "generate_static_file_task",
            static_file.id,
            bookmakers,
        )
        status = "queued"
    else:
        await static_file_service.generate_static_file(
            db=db,
            static_file=static_file,
            bookmakers=bookmakers,
        )
        await db.commit()
        status = "completed"

    return GenerateResponse(
        request_id=request_data.id,
        status=status,
        path=static_file.path,
    )


@router.get("/files/{request_id}", response_model=FileInfoResponse)
async def get_file_info(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get information about a generated static file."""
    static_file = await static_file_service.get_static_file_by_request_id(
        db=db,
        request_id=request_id,
    )
    if not static_file:
        raise HTTPException(status_code=404, detail="File not found")

    status = "completed" if static_file.hash else "pending"
    return FileInfoResponse(
        request_id=request_id,
        status=status,
        path=static_file.path,
        hash=static_file.hash,
        updated_at=static_file.updated_at,
    )


@router.get("/static/{year}/{month}/{filename}")
async def serve_static_file(year: int, month: int, filename: str):
    """Serve generated static JSON files."""
    path = f"{year}/{month:02d}/{filename}"
    full_path = static_file_service.static_path / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=full_path, media_type="application/json")
