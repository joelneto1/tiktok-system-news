from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.log_entry import LogEntry
from app.models.user import User
from app.schemas.log import LogListResponse, LogOut

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=LogListResponse)
async def list_logs(
    page: int = 1,
    page_size: int = 100,
    job_id: str | None = None,
    video_id: str | None = None,
    level: str | None = None,
    stage: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Paginated log listing with optional filters. Ordered by timestamp DESC."""
    query = select(LogEntry)
    count_query = select(func.count()).select_from(LogEntry)

    # Apply filters
    if job_id:
        query = query.where(LogEntry.job_id == job_id)
        count_query = count_query.where(LogEntry.job_id == job_id)
    if video_id:
        query = query.where(LogEntry.video_id == video_id)
        count_query = count_query.where(LogEntry.video_id == video_id)
    if level:
        query = query.where(LogEntry.level == level.upper())
        count_query = count_query.where(LogEntry.level == level.upper())
    if stage:
        query = query.where(LogEntry.stage == stage)
        count_query = count_query.where(LogEntry.stage == stage)
    if search:
        query = query.where(LogEntry.message.ilike(f"%{search}%"))
        count_query = count_query.where(LogEntry.message.ilike(f"%{search}%"))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(LogEntry.timestamp.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return LogListResponse(
        logs=[
            LogOut(
                id=str(log.id),
                video_id=str(log.video_id) if log.video_id else None,
                job_id=log.job_id,
                stage=log.stage,
                level=log.level,
                message=log.message,
                metadata_json=log.metadata_json,
                timestamp=log.timestamp,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
