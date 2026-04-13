import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session_factory
from app.models.reference import Reference
from app.models.sfx import SoundEffect
from app.models.system_prompt import SystemPrompt
from app.models.system_settings import SystemSettings
from app.models.video import Video
from app.pipeline.registry import get_pipeline
from app.queue.celery_app import celery_app
from app.queue.progress import update_progress
from app.utils.logger import logger


@celery_app.task(
    name="app.queue.tasks.pipeline_task", bind=True, max_retries=2
)
def pipeline_task(self, video_id: str, model_type: str = "news_tradicional"):
    """Main Celery task that runs the video generation pipeline."""
    print(f"[Pipeline] Task iniciada: video={video_id}, model={model_type}", flush=True)

    def _create_fresh_engine():
        """Recreate the database engine and session factory."""
        import app.database as db_module
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from app.config import settings

        db_url = settings.DATABASE_URL.split("?")[0]
        try:
            db_module.engine.dispose(close=True)
        except Exception:
            pass
        db_module.engine = create_async_engine(
            db_url, echo=False, pool_size=5, max_overflow=5,
            pool_pre_ping=False, connect_args={"ssl": False},
        )
        db_module.async_session_factory = async_sessionmaker(
            bind=db_module.engine, class_=AsyncSession, expire_on_commit=False,
        )

    try:
        # Create fresh event loop + engine for each task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _create_fresh_engine()
        try:
            loop.run_until_complete(_run_pipeline(self, video_id, model_type))
        finally:
            loop.close()
    except Exception as exc:
        print(f"[Pipeline] ERRO: {exc}", flush=True)
        try:
            loop2 = asyncio.new_event_loop()
            asyncio.set_event_loop(loop2)
            _create_fresh_engine()
            try:
                loop2.run_until_complete(
                    update_progress(video_id, "failed", "failed", str(exc)[:500])
                )
            finally:
                loop2.close()
        except Exception:
            pass
        raise


async def _run_pipeline(task, video_id: str, model_type: str) -> None:
    """Async pipeline execution.

    Opens a SHORT-LIVED session to load all data needed, closes it,
    then runs the pipeline without holding a DB connection open for minutes.
    """

    # ── Phase 1: Load all data from DB (short session) ──────────────
    async with async_session_factory() as db:
        result = await db.execute(select(Video).where(Video.id == video_id))
        video = result.scalar_one_or_none()

        if not video:
            raise ValueError(f"Video {video_id} not found")

        # Capture all values we need BEFORE closing the session
        topic = video.topic
        language = video.language
        user_id = video.user_id
        vid = str(video.id)
        voice_id = (video.metadata_json or {}).get("voice_id", "")

        # If no voice_id from frontend, load default from Settings
        if not voice_id:
            voice_result = await db.execute(
                select(SystemSettings).where(SystemSettings.key == "default_voice_id")
            )
            voice_setting = voice_result.scalar_one_or_none()
            if voice_setting:
                voice_id = voice_setting.value
                if voice_setting.is_encrypted:
                    from app.utils.crypto import decrypt_value
                    voice_id = decrypt_value(voice_id)
                print(f"[Pipeline] Voice ID do Settings: {voice_id}", flush=True)
        audio_id = (video.metadata_json or {}).get("audio_id")
        reference_id = video.reference_id

        # Mark as processing
        video.status = "processing"
        video.started_at = datetime.now(timezone.utc)
        video.celery_task_id = task.request.id
        await db.commit()

        # Load system prompts
        prompt_result = await db.execute(
            select(SystemPrompt).where(
                SystemPrompt.model_type.in_([model_type, None]),
                SystemPrompt.is_active == True,  # noqa: E712
            )
        )
        prompts_db = prompt_result.scalars().all()
        system_prompts = {p.key: p.content for p in prompts_db}

        # Resolve reference MinIO path
        reference_path: str | None = None
        if reference_id:
            ref_result = await db.execute(
                select(Reference).where(Reference.id == reference_id)
            )
            ref = ref_result.scalar_one_or_none()
            if ref:
                reference_path = ref.minio_path
                print(f"[Pipeline] Referencia: {ref.name} -> {reference_path}", flush=True)
            else:
                print(f"[Pipeline] AVISO: Reference ID {reference_id} nao encontrado no banco!", flush=True)
        else:
            print("[Pipeline] AVISO: Nenhuma referencia selecionada!", flush=True)

        # Load active SFX
        sfx_result = await db.execute(
            select(SoundEffect).where(
                SoundEffect.user_id == user_id,
                SoundEffect.is_active == True,  # noqa: E712
            )
        )
        sfx_records = sfx_result.scalars().all()
        sfx_paths = {s.sfx_type: s.minio_path for s in sfx_records}

        # Load selected background audio
        music_path: str | None = None
        if audio_id:
            from app.models.background_audio import BackgroundAudio
            audio_result = await db.execute(
                select(BackgroundAudio).where(BackgroundAudio.id == audio_id)
            )
            audio_record = audio_result.scalar_one_or_none()
            if audio_record:
                music_path = audio_record.minio_path

    # Session is now CLOSED — no more DB connection held open

    # ── Phase 2: Run pipeline (no DB session needed) ────────────────
    pipeline = get_pipeline(model_type, job_id=vid, video_id=vid)
    celery_task_id = task.request.id

    async def on_stage_update(stage: str, status: str, message: str = ""):
        await update_progress(vid, stage, status, message, celery_task_id)

    output_path = await pipeline.run(
        topic=topic,
        language=language,
        voice_id=voice_id,
        reference_minio_path=reference_path,
        db_session=None,  # Pipeline creates its own sessions when needed
        system_prompts=system_prompts,
        on_stage_update=on_stage_update,
        sfx_paths=sfx_paths,
        music_path=music_path,
    )

    # ── Phase 3: Persist result (fresh short session) ───────────────
    async with async_session_factory() as db:
        result = await db.execute(select(Video).where(Video.id == video_id))
        video = result.scalar_one_or_none()
        if video:
            video.output_url = output_path
            video.status = "completed"
            video.completed_at = datetime.now(timezone.utc)
            video.progress_percent = 100
            video.completed_stages = video.total_stages
            video.current_stage = "completed"
            await db.commit()

    await on_stage_update("completed", "completed", "Video finalizado!")
    logger.success(
        "Pipeline complete: video={vid}, output={out}",
        vid=video_id,
        out=output_path,
    )
