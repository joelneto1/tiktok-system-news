import asyncio
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.reference import Reference
from app.models.user import User
from app.schemas.reference import ReferenceListResponse, ReferenceOut, ReferenceRename
from app.services.minio_client import minio_client
from app.utils.activity_log import log_activity
from app.utils.logger import logger

router = APIRouter(prefix="/references", tags=["references"])

ALLOWED_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}


def _to_reference_out(ref: Reference) -> ReferenceOut:
    return ReferenceOut(
        id=str(ref.id),
        name=ref.name,
        original_filename=ref.original_filename,
        minio_path=ref.minio_path,
        thumbnail_path=ref.thumbnail_path,
        duration=ref.duration,
        file_size=ref.file_size,
        mime_type=ref.mime_type,
        created_at=ref.created_at,
    )


def _extract_duration(video_path: str) -> float | None:
    """Extract video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as exc:
        logger.warning(f"Failed to extract duration: {exc}")
    return None


def _extract_thumbnail(video_path: str, output_path: str) -> bool:
    """Extract first frame from video as JPEG. Returns True on success."""
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                output_path,
            ],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0 and Path(output_path).exists()
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning(f"Failed to extract thumbnail: {exc}")
    return False


async def _get_user_reference_by_id(reference_id: str, db: AsyncSession) -> Reference:
    """Fetch a reference by ID (no user check — used by token-auth endpoints)."""
    try:
        ref_uuid = uuid.UUID(reference_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
    result = await db.execute(select(Reference).where(Reference.id == ref_uuid))
    ref = result.scalar_one_or_none()
    if ref is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
    return ref


async def _get_user_reference(
    reference_id: str, user: User, db: AsyncSession
) -> Reference:
    """Fetch a reference owned by the given user or raise 404."""
    try:
        ref_uuid = uuid.UUID(reference_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")

    result = await db.execute(
        select(Reference).where(Reference.id == ref_uuid, Reference.user_id == user.id)
    )
    ref = result.scalar_one_or_none()
    if ref is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
    return ref


@router.post("/upload", response_model=ReferenceOut, status_code=status.HTTP_201_CREATED)
async def upload_reference(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a reference video file."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{content_type}'. Allowed: {', '.join(ALLOWED_VIDEO_TYPES.keys())}",
        )

    original_filename = file.filename or "video.mp4"
    display_name = name or Path(original_filename).stem
    file_uuid = uuid.uuid4()
    file_data = await file.read()
    file_size = len(file_data)

    # Upload video to MinIO (run in thread to not block event loop)
    minio_path = f"references/{user.id}/{file_uuid}/{original_filename}"
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, minio_client.upload_file, minio_path, file_data, content_type)
    logger.info(f"Reference uploaded to MinIO: {minio_path} ({file_size} bytes)")

    # Try to extract thumbnail and duration using temp files (in thread)
    thumbnail_path: str | None = None
    duration: float | None = None

    try:
        tmp_dir = tempfile.mkdtemp(prefix="ref_upload_")
        tmp_video = str(Path(tmp_dir) / original_filename)
        tmp_thumb = str(Path(tmp_dir) / "thumbnail.jpg")

        with open(tmp_video, "wb") as f:
            f.write(file_data)

        duration = await loop.run_in_executor(None, _extract_duration, tmp_video)
        logger.info(f"Reference duration: {duration}s")

        thumb_ok = await loop.run_in_executor(None, _extract_thumbnail, tmp_video, tmp_thumb)
        logger.info(f"Thumbnail extraction: {'OK' if thumb_ok else 'FAILED'}")

        if thumb_ok and Path(tmp_thumb).exists() and Path(tmp_thumb).stat().st_size > 0:
            thumbnail_minio_path = f"references/{user.id}/{file_uuid}/thumbnail.jpg"
            with open(tmp_thumb, "rb") as f:
                thumb_data = f.read()
            logger.info(f"Thumbnail size: {len(thumb_data)} bytes")
            await loop.run_in_executor(None, minio_client.upload_file, thumbnail_minio_path, thumb_data, "image/jpeg")
            thumbnail_path = thumbnail_minio_path
            logger.info(f"Thumbnail uploaded: {thumbnail_minio_path}")

        # Cleanup
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception as e:
        logger.warning(f"FFmpeg processing failed (non-critical): {e}")
        import traceback
        logger.debug(traceback.format_exc())

    reference = Reference(
        id=file_uuid,
        user_id=user.id,
        name=display_name,
        original_filename=original_filename,
        minio_path=minio_path,
        thumbnail_path=thumbnail_path,
        duration=duration,
        file_size=file_size,
        mime_type=content_type,
    )
    db.add(reference)
    await db.flush()
    await db.refresh(reference)

    await log_activity(db, "SUCCESS", f"Video de referencia enviado: {display_name} ({file_size} bytes)", stage="upload")

    return _to_reference_out(reference)


@router.get("", response_model=ReferenceListResponse)
async def list_references(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all reference videos for the current user."""
    result = await db.execute(
        select(Reference)
        .where(Reference.user_id == user.id)
        .order_by(Reference.created_at.desc())
    )
    refs = result.scalars().all()

    count_result = await db.execute(
        select(func.count()).select_from(Reference).where(Reference.user_id == user.id)
    )
    total = count_result.scalar() or 0

    return ReferenceListResponse(
        references=[_to_reference_out(r) for r in refs],
        total=total,
    )


@router.get("/{reference_id}", response_model=ReferenceOut)
async def get_reference(
    reference_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a single reference video by ID."""
    ref = await _get_user_reference(reference_id, user, db)
    return _to_reference_out(ref)


@router.patch("/{reference_id}/rename", response_model=ReferenceOut)
async def rename_reference(
    reference_id: str,
    data: ReferenceRename,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Rename a reference video."""
    ref = await _get_user_reference(reference_id, user, db)
    old_name = ref.name
    ref.name = data.name
    await db.flush()
    await db.refresh(ref)
    new_name = ref.name
    await log_activity(db, "INFO", f"Referencia renomeada: {old_name} -> {new_name}", stage="upload")
    return _to_reference_out(ref)


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference(
    reference_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a reference video from MinIO and the database."""
    ref = await _get_user_reference(reference_id, user, db)
    ref_name = ref.name

    # Delete video file from MinIO
    try:
        minio_client.delete_object(ref.minio_path)
    except Exception as exc:
        logger.warning(f"Failed to delete MinIO object {ref.minio_path}: {exc}")

    # Delete thumbnail from MinIO if it exists
    if ref.thumbnail_path:
        try:
            minio_client.delete_object(ref.thumbnail_path)
        except Exception as exc:
            logger.warning(f"Failed to delete MinIO thumbnail {ref.thumbnail_path}: {exc}")

    await db.delete(ref)
    await log_activity(db, "WARNING", f"Referencia excluida: {ref_name}", stage="upload")


@router.get("/{reference_id}/download")
async def download_reference(
    reference_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return a presigned URL for downloading the reference video.

    Public endpoint — returns a redirect to a time-limited MinIO presigned URL.
    Safe because presigned URLs expire after 1 hour.
    """
    ref = await _get_user_reference_by_id(reference_id, db)
    url = minio_client.presign_url(ref.minio_path)
    return RedirectResponse(url=url)


@router.get("/{reference_id}/thumbnail")
async def get_thumbnail(
    reference_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return a presigned URL for the reference thumbnail. Public endpoint."""
    ref = await _get_user_reference_by_id(reference_id, db)
    if not ref.thumbnail_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No thumbnail available for this reference",
        )
    url = minio_client.presign_url(ref.thumbnail_path)
    return RedirectResponse(url=url)
