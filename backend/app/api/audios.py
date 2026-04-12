"""CRUD endpoints for background audio files."""

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
from app.models.background_audio import BackgroundAudio
from app.models.user import User
from app.services.minio_client import minio_client
from app.utils.activity_log import log_activity
from app.utils.logger import logger

router = APIRouter(prefix="/audios", tags=["audios"])

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


def _extract_audio_duration(audio_path: str) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
        logger.warning(f"Failed to get audio duration: {e}")
    return None


def _to_audio_out(audio: BackgroundAudio) -> dict:
    return {
        "id": str(audio.id),
        "name": audio.name,
        "original_filename": audio.original_filename,
        "minio_path": audio.minio_path,
        "duration": audio.duration,
        "file_size": audio.file_size,
        "mime_type": audio.mime_type,
        "created_at": audio.created_at.isoformat() if audio.created_at else None,
    }


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_audio(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a background audio file."""
    content_type = file.content_type or ""
    # Be lenient with content types
    if not content_type.startswith("audio/") and content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid audio type: {content_type}")

    original_filename = file.filename or "audio.mp3"
    display_name = name or Path(original_filename).stem
    file_uuid = uuid.uuid4()
    file_data = await file.read()
    file_size = len(file_data)

    # Upload to MinIO in thread
    minio_path = f"audios/{user.id}/{file_uuid}/{original_filename}"
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, minio_client.upload_file, minio_path, file_data, content_type or "audio/mpeg")
    logger.info(f"Audio uploaded: {minio_path} ({file_size} bytes)")

    # Extract duration in thread
    duration = None
    try:
        with tempfile.NamedTemporaryFile(suffix=Path(original_filename).suffix, delete=False) as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
        duration = await loop.run_in_executor(None, _extract_audio_duration, tmp_path)
        Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Duration extraction failed: {e}")

    audio = BackgroundAudio(
        id=file_uuid,
        user_id=user.id,
        name=display_name,
        original_filename=original_filename,
        minio_path=minio_path,
        duration=duration,
        file_size=file_size,
        mime_type=content_type or "audio/mpeg",
    )
    db.add(audio)
    await db.flush()
    await db.refresh(audio)

    await log_activity(db, "SUCCESS", f"Audio de fundo enviado: {display_name} ({file_size} bytes)", stage="upload")

    return _to_audio_out(audio)


@router.get("/")
async def list_audios(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all background audios for the current user."""
    result = await db.execute(
        select(BackgroundAudio)
        .where(BackgroundAudio.user_id == user.id, BackgroundAudio.is_active == True)
        .order_by(BackgroundAudio.created_at.desc())
    )
    audios = result.scalars().all()
    return {"audios": [_to_audio_out(a) for a in audios], "total": len(audios)}


@router.patch("/{audio_id}/rename")
async def rename_audio(
    audio_id: str,
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Rename a background audio."""
    audio = await _get_user_audio(audio_id, user, db)
    old_name = audio.name
    audio.name = name
    await db.flush()
    await db.refresh(audio)
    await log_activity(db, "INFO", f"Audio renomeado: {old_name} -> {name}", stage="upload")
    return _to_audio_out(audio)


@router.delete("/{audio_id}", status_code=204)
async def delete_audio(
    audio_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a background audio."""
    audio = await _get_user_audio(audio_id, user, db)
    audio_name = audio.name
    # Delete from MinIO in background
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, minio_client.delete_object, audio.minio_path)
    except Exception:
        pass
    await db.delete(audio)
    await log_activity(db, "WARNING", f"Audio excluido: {audio_name}", stage="upload")


@router.get("/{audio_id}/download")
async def download_audio(
    audio_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get presigned download URL for an audio. Public endpoint — presigned URL is time-limited."""
    audio = await _get_audio_by_id(audio_id, db)
    url = minio_client.presign_url(audio.minio_path)
    return RedirectResponse(url=url)


async def _get_audio_by_id(audio_id: str, db: AsyncSession) -> BackgroundAudio:
    """Fetch audio by ID (no user check — for public download endpoint)."""
    try:
        aid = uuid.UUID(audio_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Audio not found")
    result = await db.execute(select(BackgroundAudio).where(BackgroundAudio.id == aid))
    audio = result.scalar_one_or_none()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    return audio


async def _get_user_audio(audio_id: str, user: User, db: AsyncSession) -> BackgroundAudio:
    try:
        aid = uuid.UUID(audio_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Audio not found")
    result = await db.execute(
        select(BackgroundAudio).where(BackgroundAudio.id == aid, BackgroundAudio.user_id == user.id)
    )
    audio = result.scalar_one_or_none()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    return audio
