import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.video import Video
from app.models.user import User
from app.schemas.video import VideoListResponse, VideoOut
from app.services.minio_client import minio_client
from app.utils.logger import logger

router = APIRouter(prefix="/videos", tags=["videos"])


def _to_video_out(video: Video) -> VideoOut:
    return VideoOut(
        id=str(video.id),
        topic=video.topic,
        language=video.language,
        model_type=video.model_type,
        status=video.status,
        current_stage=video.current_stage,
        progress_percent=video.progress_percent,
        total_stages=video.total_stages,
        completed_stages=video.completed_stages,
        attempts=video.attempts,
        script=video.script,
        output_url=video.output_url,
        error_message=video.error_message,
        reference_id=str(video.reference_id) if video.reference_id else None,
        started_at=video.started_at,
        completed_at=video.completed_at,
        created_at=video.created_at,
    )


async def _get_user_video(video_id: str, user: User, db: AsyncSession) -> Video:
    """Fetch a video owned by the given user or raise 404."""
    try:
        vid_uuid = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    result = await db.execute(
        select(Video).where(Video.id == vid_uuid, Video.user_id == user.id)
    )
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return video


@router.get("/", response_model=VideoListResponse)
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List videos for the current user with pagination and optional status filter."""
    query = select(Video).where(Video.user_id == user.id)
    count_query = select(func.count()).select_from(Video).where(Video.user_id == user.id)

    if status_filter:
        query = query.where(Video.status == status_filter)
        count_query = count_query.where(Video.status == status_filter)

    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Video.created_at.desc()).offset(offset).limit(page_size)
    )
    videos = result.scalars().all()

    return VideoListResponse(
        videos=[_to_video_out(v) for v in videos],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a single video by ID."""
    video = await _get_user_video(video_id, user, db)
    return _to_video_out(video)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a video and its associated MinIO assets."""
    video = await _get_user_video(video_id, user, db)

    # Delete MinIO assets
    minio_prefix = f"videos/{user.id}/{video.id}/"
    try:
        objects = minio_client.list_objects(prefix=minio_prefix)
        for obj in objects:
            minio_client.delete_object(obj["name"])
    except Exception as exc:
        logger.warning(f"Failed to delete MinIO objects for video {video.id}: {exc}")

    # Also try to delete the output URL object if it's a MinIO path
    if video.output_url and not video.output_url.startswith("http"):
        try:
            minio_client.delete_object(video.output_url)
        except Exception as exc:
            logger.warning(f"Failed to delete output file {video.output_url}: {exc}")

    await db.delete(video)


@router.get("/{video_id}/download")
async def download_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return a presigned URL for downloading the rendered video."""
    video = await _get_user_video(video_id, user, db)

    if not video.output_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video output is not yet available",
        )

    # If output_url is already an external URL, redirect directly
    if video.output_url.startswith("http"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=video.output_url)

    # Otherwise treat it as a MinIO path
    from fastapi.responses import RedirectResponse
    url = minio_client.presign_url(video.output_url)
    return RedirectResponse(url=url)


@router.get("/{video_id}/script")
async def get_script(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the generated script text for a video."""
    video = await _get_user_video(video_id, user, db)

    script_text = video.script

    # Fallback: try MinIO if DB field is empty
    if not script_text:
        from app.processing.asset_manager import asset_manager
        script_text = asset_manager.try_download_text(str(video.id), "stage1", "script.txt")

    if not script_text:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script is not yet available for this video",
        )

    return {"video_id": str(video.id), "script": script_text}
