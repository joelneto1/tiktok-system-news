import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import async_session_factory
from app.models.log_entry import LogEntry
from app.models.video import Video
from app.utils.logger import logger

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/pipeline/{video_id}")
async def pipeline_progress(websocket: WebSocket, video_id: str):
    """WebSocket endpoint for real-time pipeline progress.

    Sends JSON messages with video status and new log entries every 2 s.
    The client connects when the pipeline starts and receives updates
    until the pipeline reaches ``completed`` or ``failed``.

    Message types:
    - ``{"type": "status", "data": {...}}``   -- video status snapshot
    - ``{"type": "log",    "data": {...}}``   -- individual log entry
    - ``{"type": "done",   "data": {...}}``   -- terminal message (pipeline finished)
    """
    await websocket.accept()
    logger.info("WebSocket connected for video {vid}", vid=video_id)

    last_log_count = 0
    last_status_key = ""

    try:
        while True:
            async with async_session_factory() as db:
                # ── Video status ─────────────────────────────────────
                result = await db.execute(
                    select(Video).where(Video.id == video_id)
                )
                video = result.scalar_one_or_none()

                if not video:
                    await websocket.send_json({"error": "Video not found"})
                    break

                # Only send when something changed
                status_key = (
                    f"{video.status}:{video.current_stage}:"
                    f"{video.progress_percent}"
                )
                if status_key != last_status_key:
                    await websocket.send_json(
                        {
                            "type": "status",
                            "data": {
                                "status": video.status,
                                "current_stage": video.current_stage,
                                "progress_percent": video.progress_percent,
                                "completed_stages": video.completed_stages,
                                "total_stages": video.total_stages,
                            },
                        }
                    )
                    last_status_key = status_key

                # ── New log entries ──────────────────────────────────
                log_result = await db.execute(
                    select(LogEntry)
                    .where(LogEntry.video_id == video_id)
                    .order_by(LogEntry.timestamp)
                    .offset(last_log_count)
                )
                new_logs = log_result.scalars().all()

                for log in new_logs:
                    await websocket.send_json(
                        {
                            "type": "log",
                            "data": {
                                "level": log.level,
                                "stage": log.stage,
                                "message": log.message,
                                "timestamp": (
                                    log.timestamp.isoformat()
                                    if log.timestamp
                                    else ""
                                ),
                            },
                        }
                    )
                last_log_count += len(new_logs)

                # ── Terminal check ───────────────────────────────────
                if video.status in ("completed", "failed"):
                    await websocket.send_json(
                        {
                            "type": "done",
                            "data": {
                                "status": video.status,
                                "output_url": video.output_url,
                                "error_message": video.error_message,
                            },
                        }
                    )
                    break

            # Poll interval
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for video {vid}", vid=video_id)
    except Exception as exc:
        logger.error(
            "WebSocket error for video {vid}: {err}", vid=video_id, err=exc
        )
