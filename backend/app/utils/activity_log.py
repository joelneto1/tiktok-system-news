"""Activity logging — writes structured log entries to the database.

Usage:
    from app.utils.activity_log import log_activity

    await log_activity(db, "INFO", "Reference uploaded: video.mp4", stage="upload")
    await log_activity(db, "SUCCESS", "Settings saved", stage="settings")
    await log_activity(db, "ERROR", "Upload failed: timeout", stage="upload")
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_entry import LogEntry
from app.utils.logger import logger


async def log_activity(
    db: AsyncSession,
    level: str,
    message: str,
    stage: str | None = None,
    job_id: str | None = None,
    video_id: str | None = None,
    metadata: dict | None = None,
):
    """Write a log entry to the database AND to loguru console.

    Args:
        db: Database session (will flush but not commit — caller commits)
        level: INFO, SUCCESS, WARNING, ERROR, DEBUG
        message: Human-readable log message
        stage: Optional stage/category (upload, settings, auth, pipeline, etc.)
        job_id: Optional job/celery task ID
        video_id: Optional video UUID string
        metadata: Optional extra data dict
    """
    # Write to console via loguru
    log_func = {
        "DEBUG": logger.debug,
        "INFO": logger.info,
        "SUCCESS": logger.success,
        "WARNING": logger.warning,
        "ERROR": logger.error,
    }.get(level.upper(), logger.info)

    prefix = f"[{stage}] " if stage else ""
    log_func(f"{prefix}{message}")

    # Write to database
    try:
        import uuid as _uuid
        vid = None
        if video_id:
            try:
                vid = _uuid.UUID(video_id)
            except ValueError:
                pass

        entry = LogEntry(
            video_id=vid,
            job_id=job_id,
            stage=stage,
            level=level.upper(),
            message=message,
            metadata_json=metadata,
        )
        db.add(entry)
        await db.flush()
    except Exception as e:
        # Never let logging break the main operation
        logger.warning(f"Failed to write log to DB: {e}")


async def log_activity_standalone(
    level: str,
    message: str,
    stage: str | None = None,
    job_id: str | None = None,
    video_id: str | None = None,
    metadata: dict | None = None,
):
    """Write a log entry using a standalone session (for use outside request context)."""
    from app.database import async_session_factory

    # Console log
    log_func = {
        "DEBUG": logger.debug,
        "INFO": logger.info,
        "SUCCESS": logger.success,
        "WARNING": logger.warning,
        "ERROR": logger.error,
    }.get(level.upper(), logger.info)

    prefix = f"[{stage}] " if stage else ""
    log_func(f"{prefix}{message}")

    try:
        import uuid as _uuid
        vid = None
        if video_id:
            try:
                vid = _uuid.UUID(video_id)
            except ValueError:
                pass

        async with async_session_factory() as session:
            entry = LogEntry(
                video_id=vid,
                job_id=job_id,
                stage=stage,
                level=level.upper(),
                message=message,
                metadata_json=metadata,
            )
            session.add(entry)
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to write standalone log to DB: {e}")
