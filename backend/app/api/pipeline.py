import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.video import Video
from app.schemas.pipeline import PipelineStartRequest, PipelineStatusResponse, StageInfo
from app.schemas.video import VideoOut
from app.utils.activity_log import log_activity

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# Pipeline stage definitions — names MUST match on_stage_update() calls in pipeline.py
PIPELINE_STAGES = [
    {"name": "stage1_script", "description": "Gerar roteiro com IA"},
    {"name": "stage1_tts", "description": "Narracao TTS (texto para voz)"},
    {"name": "stage2_avatar", "description": "Avatar DreamFace + Chromakey"},
    {"name": "stage2_brolls", "description": "B-Rolls (Grok Imagine)"},
    {"name": "stage3_render", "description": "Renderizacao final (Remotion)"},
    {"name": "completed", "description": "Video finalizado e salvo"},
]


def _video_to_out(video: Video) -> VideoOut:
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


def _build_stages(video: Video) -> list[StageInfo]:
    """Build stage info list based on current video state."""
    stages: list[StageInfo] = []
    current_found = False

    for stage_def in PIPELINE_STAGES:
        name = stage_def["name"]

        if video.status == "completed":
            stage_status = "completed"
        elif video.status == "failed" and video.current_stage == name:
            stage_status = "failed"
            current_found = True
        elif video.current_stage == name:
            stage_status = "in_progress"
            current_found = True
        elif not current_found and video.current_stage is not None:
            # Stages before current are completed
            stage_status = "completed"
        else:
            stage_status = "pending"

        stages.append(
            StageInfo(
                name=name,
                description=stage_def["description"],
                status=stage_status,
            )
        )

    return stages


@router.post("/start", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
async def start_pipeline(
    data: PipelineStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Video record and start the pipeline.

    Dispatches a Celery task (placeholder for now).
    """
    reference_id = uuid.UUID(data.reference_id) if data.reference_id else None

    video = Video(
        user_id=current_user.id,
        topic=data.topic,
        language=data.language,
        model_type=data.model_type,
        reference_id=reference_id,
        status="queued",
        current_stage=None,
        total_stages=len(PIPELINE_STAGES),
        metadata_json={
            "voice_id": data.voice_id,
            "audio_id": data.audio_id,
        },
    )
    db.add(video)
    await db.flush()
    await db.refresh(video)

    # Dispatch Celery task
    from app.queue.tasks import pipeline_task

    task = pipeline_task.delay(str(video.id), data.model_type)
    video.celery_task_id = task.id
    video.status = "processing"
    video.started_at = datetime.now(timezone.utc)
    await db.flush()

    await log_activity(db, "SUCCESS", f"Pipeline iniciado: {data.topic[:50]}... (modelo: {data.model_type})", stage="pipeline", video_id=str(video.id))

    return _video_to_out(video)


@router.post("/enqueue", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
async def enqueue_pipeline(
    data: PipelineStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Video record with status='queued' for later processing."""
    reference_id = uuid.UUID(data.reference_id) if data.reference_id else None

    video = Video(
        user_id=current_user.id,
        topic=data.topic,
        language=data.language,
        model_type=data.model_type,
        reference_id=reference_id,
        status="queued",
        total_stages=len(PIPELINE_STAGES),
        metadata_json={
            "voice_id": data.voice_id,
        },
    )
    db.add(video)
    await db.flush()
    await db.refresh(video)

    # Dispatch Celery task (queues behind any running job, stays 'queued' until it starts)
    from app.queue.tasks import pipeline_task
    task = pipeline_task.delay(str(video.id), data.model_type)
    video.celery_task_id = task.id
    # Keep status as 'queued' — task.py changes to 'processing' when it actually starts
    await db.flush()

    await log_activity(db, "INFO", f"Pipeline na fila: {data.topic[:50]}... (task={task.id})", stage="pipeline", video_id=str(video.id))
    return _video_to_out(video)


@router.post("/{video_id}/retry", response_model=VideoOut)
async def retry_pipeline(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry a failed/stalled pipeline from where it left off."""
    try:
        vid = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Video not found")

    result = await db.execute(select(Video).where(Video.id == vid))
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    if video.status == "completed":
        raise HTTPException(status_code=400, detail="Video already completed")

    # Reset status to processing and dispatch new Celery task
    video.status = "processing"
    video.error_message = None
    video.started_at = datetime.now(timezone.utc)
    await db.flush()

    from app.queue.tasks import pipeline_task
    task = pipeline_task.delay(str(video.id), video.model_type)
    video.celery_task_id = task.id
    await db.flush()

    await log_activity(db, "INFO", f"Pipeline retomado: {video.topic[:50]}...", stage="pipeline", video_id=str(video.id))

    return _video_to_out(video)


@router.get("/{video_id}/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return video info and per-stage breakdown."""
    try:
        vid = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    result = await db.execute(select(Video).where(Video.id == vid))
    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    return PipelineStatusResponse(
        video=_video_to_out(video),
        stages=_build_stages(video),
    )
