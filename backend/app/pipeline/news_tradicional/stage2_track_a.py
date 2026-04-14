import os
import shutil
import tempfile

from app.automation.account_rotator import account_rotator
from app.automation.dreamface import dreamface_automation
import app.database as db_module
from app.processing.asset_manager import asset_manager
from app.processing.ffmpeg import ffmpeg_processor
from app.services.minio_client import minio_client
from app.utils.logger import logger


def _log_to_db(video_id: str, stage: str, message: str, level: str = "INFO"):
    """Save a log entry to the database using SYNCHRONOUS connection."""
    try:
        import uuid
        import psycopg2
        from app.config import settings
        db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").split("?")[0]
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO log_entries (id, video_id, stage, level, message) VALUES (%s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), video_id, stage, level, message)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


async def process_avatar(
    job_id: str,
    reference_minio_path: str,
    tts_audio_minio_path: str,
    topic: str,
    db_session=None,
    on_progress: callable = None,
) -> dict:
    """Stage 2 Track A: Generate lip-synced avatar with transparent background.

    Flow:
    1. Get next available DreamFace account (round-robin)
    2. Download reference video + TTS audio from MinIO to temp files
    3. Run DreamFace automation (upload -> process -> download)
    4. Apply chromakey (FFmpeg) to remove green screen
    5. Convert to WebM with alpha channel for Remotion
    6. Upload processed avatar to MinIO
    7. Cleanup temp files

    Args:
        job_id: Pipeline job ID.
        reference_minio_path: MinIO path to reference video (green screen).
        tts_audio_minio_path: MinIO path to TTS audio.
        topic: Video topic (for project naming).
        db_session: Database session for account queries.
        on_progress: Optional progress callback.

    Returns:
        dict with:
        - avatar_minio_path: MinIO path to processed avatar (WebM with alpha)
        - avatar_raw_path: MinIO path to raw DreamFace output
        - duration: Avatar video duration in seconds
    """
    def log(msg, level="INFO"):
        print(f"[Track A] {msg}", flush=True)
        _log_to_db(job_id, "stage2_avatar", f"[Avatar] {msg}", level)

    log("Iniciando processamento do avatar...")

    # Step 1: Get DreamFace account
    log("Buscando conta DreamFace...")
    async with db_module.async_session_factory() as fresh_db:
        account = await account_rotator.get_next_account("dreamface", fresh_db)
        if not account:
            raise RuntimeError("No active DreamFace accounts available")
        cookies = await account_rotator.get_account_cookies(account)
        proxy = await account_rotator.get_account_proxy(account)

    log(f"Conta DreamFace: {account.account_name}")

    tmp_dir = tempfile.mkdtemp(prefix=f"dreamface_{job_id}_")

    try:
        short_id = job_id[:8]
        ref_local = os.path.join(tmp_dir, f"avatar_ref_{short_id}.mp4")
        audio_local = os.path.join(tmp_dir, f"news_{short_id}.mp3")

        log(f"Baixando video de referencia do MinIO: {reference_minio_path}")
        ref_data = minio_client.download_file(reference_minio_path)
        with open(ref_local, "wb") as f:
            f.write(ref_data)
        log(f"Video de referencia baixado: {len(ref_data)/1024/1024:.1f}MB -> {ref_local}")

        log("Baixando audio TTS do MinIO...")
        audio_data = minio_client.download_file(tts_audio_minio_path)
        with open(audio_local, "wb") as f:
            f.write(audio_data)
        log("Audio TTS baixado!")

        log("Enviando para DreamFace...")

        # Progress callback that saves to DB
        def df_progress(msg):
            log(f"DreamFace: {msg}")

        # Step 3: Run DreamFace automation
        raw_avatar_path = await dreamface_automation.process_avatar(
            account_id=str(account.id),
            cookies=cookies,
            proxy=proxy,
            reference_video_path=ref_local,
            tts_audio_path=audio_local,
            project_name=f"News {job_id[:8]}: {topic[:40]}",
            timeout=600,
            on_progress=df_progress,
        )

        # Mark account as successfully used
        await account_rotator.mark_account_used(
            account, success=True
        )

        log("Avatar gerado pelo DreamFace! Salvando no MinIO...", "SUCCESS")

        # Step 4: Upload raw DreamFace result to MinIO
        raw_minio_path = asset_manager.save_asset_from_file(
            job_id, "stage2_avatar", "avatar_raw.mp4", raw_avatar_path, "video/mp4"
        )
        log(f"Avatar raw salvo: {raw_minio_path}")

        # Step 5: Apply chromakey to remove green screen
        log("Aplicando chromakey (removendo fundo verde)...")
        chromakey_output = os.path.join(tmp_dir, "avatar_chromakey.avi")
        await ffmpeg_processor.chromakey(
            input_path=raw_avatar_path,
            output_path=chromakey_output,
        )

        log("Chromakey concluido! Convertendo para WebM com alpha...")

        # Step 6: Convert to WebM VP9 with alpha channel (for Remotion)
        webm_output = os.path.join(tmp_dir, "avatar_alpha.webm")
        await ffmpeg_processor.convert_to_webm_alpha(
            input_path=chromakey_output,
            output_path=webm_output,
        )

        # Step 7: Get duration
        duration = await ffmpeg_processor.get_duration(webm_output)

        # Step 8: Upload final avatar to MinIO
        avatar_minio_path = asset_manager.save_asset_from_file(
            job_id, "stage2_avatar", "avatar_alpha.webm", webm_output, "video/webm"
        )

        logger.success(
            "[Track A] Avatar complete: {path} ({dur:.1f}s)",
            path=avatar_minio_path,
            dur=duration,
        )

        return {
            "avatar_minio_path": avatar_minio_path,
            "avatar_raw_path": raw_minio_path,
            "duration": duration,
        }

    except Exception as e:
        # Mark account as failed
        try:
            await account_rotator.mark_account_used(
                account, success=False, error_message=str(e)
            )
        except Exception:
            pass
        logger.error("[Track A] Avatar processing failed: {err}", err=e)
        raise

    finally:
        # Cleanup temp files
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            logger.debug("[Track A] Cleaned up temp dir: {d}", d=tmp_dir)
        except Exception:
            pass
