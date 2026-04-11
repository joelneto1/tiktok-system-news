"""CRUD endpoints for sound effect (SFX) files."""

import asyncio
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.sfx import SoundEffect
from app.models.user import User
from app.services.minio_client import minio_client
from app.utils.activity_log import log_activity
from app.utils.logger import logger

router = APIRouter(prefix="/sfx", tags=["sfx"])

ALLOWED_AUDIO_TYPES = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/flac": ".flac",
}

VALID_SFX_TYPES = {"whoosh", "impact", "ding", "tension_rise", "news_flash"}


def _extract_audio_duration(audio_path: str) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
        logger.warning(f"Failed to get SFX duration: {e}")
    return None


def _to_sfx_out(sfx: SoundEffect) -> dict:
    return {
        "id": str(sfx.id),
        "name": sfx.name,
        "sfx_type": sfx.sfx_type,
        "original_filename": sfx.original_filename,
        "minio_path": sfx.minio_path,
        "duration": sfx.duration,
        "file_size": sfx.file_size,
        "mime_type": sfx.mime_type,
        "created_at": sfx.created_at.isoformat() if sfx.created_at else None,
    }


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_sfx(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    sfx_type: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a sound effect file."""
    if sfx_type not in VALID_SFX_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid sfx_type: {sfx_type}. Must be one of: {', '.join(sorted(VALID_SFX_TYPES))}")

    content_type = file.content_type or ""
    if not content_type.startswith("audio/") and content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid audio type: {content_type}")

    original_filename = file.filename or "sfx.mp3"
    display_name = name or Path(original_filename).stem
    file_uuid = uuid.uuid4()
    file_data = await file.read()
    file_size = len(file_data)

    # Deactivate any existing SFX of the same type for this user
    existing = await db.execute(
        select(SoundEffect).where(
            SoundEffect.user_id == user.id,
            SoundEffect.sfx_type == sfx_type,
            SoundEffect.is_active == True,
        )
    )
    for old_sfx in existing.scalars().all():
        old_sfx.is_active = False

    # Upload to MinIO
    minio_path = f"sfx/{user.id}/{file_uuid}/{original_filename}"
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, minio_client.upload_file, minio_path, file_data, content_type or "audio/mpeg")
    logger.info(f"SFX uploaded: {minio_path} ({file_size} bytes)")

    # Extract duration
    duration = None
    try:
        with tempfile.NamedTemporaryFile(suffix=Path(original_filename).suffix, delete=False) as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
        duration = await loop.run_in_executor(None, _extract_audio_duration, tmp_path)
        Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"SFX duration extraction failed: {e}")

    sfx = SoundEffect(
        id=file_uuid,
        user_id=user.id,
        name=display_name,
        sfx_type=sfx_type,
        original_filename=original_filename,
        minio_path=minio_path,
        duration=duration,
        file_size=file_size,
        mime_type=content_type or "audio/mpeg",
    )
    db.add(sfx)
    await db.flush()
    await db.refresh(sfx)

    await log_activity(db, "SUCCESS", f"SFX enviado: {display_name} (tipo: {sfx_type}, {file_size} bytes)", stage="upload")

    return _to_sfx_out(sfx)


@router.get("/")
async def list_sfx(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all active SFX for the current user."""
    result = await db.execute(
        select(SoundEffect)
        .where(SoundEffect.user_id == user.id, SoundEffect.is_active == True)
        .order_by(SoundEffect.sfx_type, SoundEffect.created_at.desc())
    )
    sfx_list = result.scalars().all()
    return {"sfx": [_to_sfx_out(s) for s in sfx_list], "total": len(sfx_list)}


@router.delete("/{sfx_id}", status_code=204)
async def delete_sfx(
    sfx_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a sound effect."""
    sfx = await _get_user_sfx(sfx_id, user, db)
    sfx_name = sfx.name
    sfx_type = sfx.sfx_type
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, minio_client.delete_object, sfx.minio_path)
    except Exception:
        pass
    await db.delete(sfx)
    await log_activity(db, "WARNING", f"SFX excluido: {sfx_name} (tipo: {sfx_type})", stage="upload")


@router.get("/{sfx_id}/download")
async def download_sfx(
    sfx_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get presigned download URL for a SFX. Public endpoint — presigned URL is time-limited."""
    sfx = await _get_sfx_by_id(sfx_id, db)
    url = minio_client.presign_url(sfx.minio_path)
    return RedirectResponse(url=url)


async def _get_sfx_by_id(sfx_id: str, db: AsyncSession) -> SoundEffect:
    """Fetch SFX by ID (no user check — for public download endpoint)."""
    try:
        sid = uuid.UUID(sfx_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="SFX not found")
    result = await db.execute(select(SoundEffect).where(SoundEffect.id == sid))
    sfx = result.scalar_one_or_none()
    if not sfx:
        raise HTTPException(status_code=404, detail="SFX not found")
    return sfx


async def _get_user_sfx(sfx_id: str, user: User, db: AsyncSession) -> SoundEffect:
    try:
        sid = uuid.UUID(sfx_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="SFX not found")
    result = await db.execute(
        select(SoundEffect).where(SoundEffect.id == sid, SoundEffect.user_id == user.id)
    )
    sfx = result.scalar_one_or_none()
    if not sfx:
        raise HTTPException(status_code=404, detail="SFX not found")
    return sfx
