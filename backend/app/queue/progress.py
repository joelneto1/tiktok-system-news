from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session_factory
from app.models.log_entry import LogEntry
from app.models.video import Video
from app.utils.logger import logger

STAGE_ORDER = [
    "stage1_script",
    "stage1_tts",
    "stage2_avatar",
    "stage2_brolls",
    "stage3_render",
    "completed",
]


async def update_progress(
    video_id: str,
    stage: str,
    status: str,
    message: str = "",
    job_id: str | None = None,
) -> None:
    """Update pipeline progress in the database and create a log entry.

    Args:
        video_id: Video record UUID (string).
        stage: Current stage name (one of ``STAGE_ORDER``).
        status: ``"in_progress"``, ``"completed"``, or ``"failed"``.
        message: Human-readable status message.
        job_id: Optional Celery task ID for cross-referencing.
    """
    async with async_session_factory() as session:
        try:
            # ── Update Video record ──────────────────────────────────
            result = await session.execute(
                select(Video).where(Video.id == video_id)
            )
            video = result.scalar_one_or_none()

            if video:
                video.current_stage = stage

                if status == "completed" and stage in STAGE_ORDER:
                    stage_idx = STAGE_ORDER.index(stage) + 1
                    video.completed_stages = min(stage_idx, video.total_stages)
                    video.progress_percent = int(
                        (stage_idx / len(STAGE_ORDER)) * 100
                    )

                if status == "failed":
                    video.status = "failed"
                    video.error_message = message[:500]

                if stage == "completed" and status == "completed":
                    video.status = "completed"
                    video.completed_at = datetime.now(timezone.utc)
                    video.progress_percent = 100

                video.updated_at = datetime.now(timezone.utc)

            # ── Create log entry ─────────────────────────────────────
            if status == "completed":
                level = "SUCCESS"
            elif status == "failed":
                level = "ERROR"
            else:
                level = "INFO"

            log_entry = LogEntry(
                video_id=video_id if video else None,
                job_id=job_id,
                stage=stage,
                level=level,
                message=f"[{stage}] {message}",
            )
            session.add(log_entry)

            await session.commit()

        except Exception as exc:
            await session.rollback()
            logger.error("Failed to update progress: {err}", err=exc)
