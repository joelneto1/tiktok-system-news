import os
import shutil
import tempfile

from app.automation.account_rotator import account_rotator
from app.automation.dreamface import dreamface_automation
from app.database import async_session_factory
from app.processing.asset_manager import asset_manager
from app.processing.ffmpeg import ffmpeg_processor
from app.services.minio_client import minio_client
from app.utils.logger import logger


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
    logger.info("[Track A] Starting avatar processing for job {jid}", jid=job_id)

    # Step 1: Get DreamFace account (fresh DB session)
    async with async_session_factory() as fresh_db:
        account = await account_rotator.get_next_account("dreamface", fresh_db)
        if not account:
            raise RuntimeError("No active DreamFace accounts available")
        cookies = await account_rotator.get_account_cookies(account)
        proxy = await account_rotator.get_account_proxy(account)

    logger.info(
        "[Track A] Using DreamFace account: {name}",
        name=account.account_name,
    )

    # Create temp directory for this job
    tmp_dir = tempfile.mkdtemp(prefix=f"dreamface_{job_id}_")

    try:
        # Step 2: Download assets from MinIO
        ref_local = os.path.join(tmp_dir, "reference.mp4")
        audio_local = os.path.join(tmp_dir, "tts_audio.mp3")

        ref_data = minio_client.download_file(reference_minio_path)
        with open(ref_local, "wb") as f:
            f.write(ref_data)
        logger.info(
            "[Track A] Downloaded reference: {n} bytes", n=len(ref_data)
        )

        audio_data = minio_client.download_file(tts_audio_minio_path)
        with open(audio_local, "wb") as f:
            f.write(audio_data)
        logger.info(
            "[Track A] Downloaded TTS audio: {n} bytes", n=len(audio_data)
        )

        if on_progress:
            on_progress("Uploading to DreamFace...")

        # Step 3: Run DreamFace automation
        raw_avatar_path = await dreamface_automation.process_avatar(
            account_id=str(account.id),
            cookies=cookies,
            proxy=proxy,
            reference_video_path=ref_local,
            tts_audio_path=audio_local,
            project_name=f"News: {topic[:50]}",
            timeout=600,
            on_progress=on_progress,
        )

        # Mark account as successfully used
        await account_rotator.mark_account_used(
            account, success=True
        )

        if on_progress:
            on_progress("Applying chromakey...")

        # Step 4: Upload raw DreamFace result to MinIO
        raw_minio_path = asset_manager.save_asset_from_file(
            job_id, "stage2_avatar", "avatar_raw.mp4", raw_avatar_path, "video/mp4"
        )
        logger.info("[Track A] Raw avatar saved: {path}", path=raw_minio_path)

        # Step 5: Apply chromakey to remove green screen
        chromakey_output = os.path.join(tmp_dir, "avatar_chromakey.avi")
        await ffmpeg_processor.chromakey(
            input_path=raw_avatar_path,
            output_path=chromakey_output,
            color="00FF00",
            similarity=0.3,
            blend=0.1,
        )

        if on_progress:
            on_progress("Converting to WebM with alpha...")

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
