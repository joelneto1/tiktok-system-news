import json
import os
import shutil
import tempfile

from app.automation.account_rotator import account_rotator
from app.automation.grok import grok_automation
from app.config import settings
from app.database import async_session_factory
from app.processing.asset_manager import asset_manager
from app.processing.ffmpeg import ffmpeg_processor
from app.services.minio_client import minio_client
from app.services.scene_director import scene_director
from app.services.whisper import whisper_client
from app.utils.logger import logger


def _log_to_db(video_id: str, stage: str, message: str, level: str = "INFO"):
    """Save a log entry to the database (for frontend visibility)."""
    import asyncio
    from app.models.log_entry import LogEntry

    async def _save():
        async with async_session_factory() as session:
            entry = LogEntry(video_id=video_id, stage=stage, level=level, message=message)
            session.add(entry)
            await session.commit()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_save())
        else:
            asyncio.run(_save())
    except Exception:
        pass


async def process_brolls(
    job_id: str,
    tts_audio_minio_path: str,
    script: str,
    language: str,
    db_session,
    system_prompt_scene_director: str | None = None,
    on_progress: callable = None,
) -> dict:
    """Stage 2 Track B: Generate B-Roll videos from scene analysis.

    Flow:
        1. Download TTS audio from MinIO
        2. Transcribe with Whisper (word-level timestamps)
        3. Scene Director LLM (semantic blocks + SFX + B-Roll prompts)
        4. Get Grok account (round-robin)
        5. Batch generate B-Rolls via Grok (batch_size tabs at a time)
        6. Upload all B-Rolls to MinIO
        7. Return structured data for Remotion

    Args:
        job_id: Unique job identifier.
        tts_audio_minio_path: MinIO path to the TTS audio file.
        script: The narration script text.
        language: BCP-47 language tag (e.g. ``"pt-BR"``).
        db_session: SQLAlchemy async session for account queries.
        system_prompt_scene_director: Optional custom system prompt for
            the Scene Director LLM.
        on_progress: Optional callback for progress updates.

    Returns:
        Dict with:
        - word_timestamps: list of {word, start, end}
        - scenes: list of scene blocks with broll_prompts and sfx
        - broll_paths: dict mapping scene_index -> MinIO path
        - urgent_keywords: list of keywords for BREAKING NEWS banner
        - total_duration: audio duration in seconds
        - prompts_used: list of prompts sent to Grok
    """
    def log(msg, level="INFO"):
        print(f"[Track B] {msg}", flush=True)
        _log_to_db(job_id, "stage2_brolls", f"[B-Rolls] {msg}", level)

    log("Iniciando processamento de B-Rolls...")

    tmp_dir = tempfile.mkdtemp(prefix=f"brolls_{job_id}_")
    account = None

    try:
        # ── Step 1: Download TTS audio ────────────────────────────
        log("1/7 Baixando audio TTS do MinIO...")

        audio_local = os.path.join(tmp_dir, "tts_audio.mp3")
        audio_data = minio_client.download_file(tts_audio_minio_path)
        with open(audio_local, "wb") as f:
            f.write(audio_data)

        total_duration = await ffmpeg_processor.get_duration(audio_local)
        log(f"1/7 Audio TTS: {len(audio_data)/1024:.0f}KB, duracao: {total_duration:.1f}s", flush=True)

        # ── Step 2: Whisper transcription ─────────────────────────
        log("2/7 Transcrevendo com Whisper (word-level)...")

        word_timestamps = await whisper_client.transcribe_to_word_timestamps(
            audio_local, language=language
        )
        log(f"2/7 Whisper: {len(word_timestamps)} palavras transcritas", flush=True)

        timestamps_json = json.dumps(word_timestamps, ensure_ascii=False, indent=2)
        asset_manager.save_asset(
            job_id,
            "stage2_brolls",
            "word_timestamps.json",
            timestamps_json.encode(),
            "application/json",
        )

        # ── Step 3: Scene Director (LLM) ─────────────────────────
        log("3/7 Diretor de Cena analisando roteiro (LLM)...")

        scene_data = await scene_director.direct_scenes(
            script=script,
            word_timestamps=word_timestamps,
            total_duration=total_duration,
            system_prompt=system_prompt_scene_director,
            broll_duration=settings.BROLL_DURATION_SECONDS,
        )

        scenes = scene_data.get("scenes", [])
        urgent_keywords = scene_data.get("urgent_keywords", [])
        log(f"3/7 Diretor de Cena: {len(scenes)} cenas, {len(urgent_keywords)} keywords", flush=True)

        scene_json = json.dumps(scene_data, ensure_ascii=False, indent=2)
        asset_manager.save_asset(
            job_id,
            "stage2_brolls",
            "scenes.json",
            scene_json.encode(),
            "application/json",
        )
        log("3/7 Cenas salvas no MinIO (scenes.json)")

        # ── Step 4: Extract B-Roll prompts ────────────────────────
        prompts = [
            scene.get("broll_prompt", "")
            for scene in scenes
            if scene.get("broll_prompt")
        ]

        if not prompts:
            raise RuntimeError("[Track B] No B-Roll prompts generated by Scene Director")

        max_brolls = min(len(prompts), settings.BROLL_COUNT)
        prompts = prompts[:max_brolls]
        log(f"4/7 {len(prompts)} prompts de B-Roll extraidos:", flush=True)
        for i, p in enumerate(prompts):
            log(f"  [{i+1}] {p[:80]}")

        # ── Step 5: Get Grok account ─────────────────────────────
        log("5/7 Buscando conta Grok...")
        async with async_session_factory() as fresh_db:
            account = await account_rotator.get_next_account("grok", fresh_db)
            if not account:
                raise RuntimeError("No active Grok accounts available")
            cookies = await account_rotator.get_account_cookies(account)
            proxy = await account_rotator.get_account_proxy(account)
        log(f"5/7 Conta Grok: {account.account_name} ({len(cookies)} cookies)", flush=True)

        # ── Step 6: Batch generate via Grok ──────────────────────
        log(f"6/7 Gerando {len(prompts)} B-Rolls com Grok...", flush=True)

        def _grok_progress(done: int, total: int, msg: str) -> None:
            log(f"6/7 B-Rolls: {done}/{total} - {msg}", flush=True)
            if on_progress:
                on_progress(f"B-Rolls: {done}/{total} - {msg}")

        broll_local_paths = await grok_automation.batch_generate(
            prompts=prompts,
            account_id=str(account.id),
            cookies=cookies,
            proxy=proxy,
            batch_size=settings.BROLL_BATCH_SIZE,
            max_retries=2,
            timeout_per_video=300,
            on_progress=_grok_progress,
        )

        await account_rotator.mark_account_used(account, success=True)
        log(f"6/7 Grok concluido: {len(broll_local_paths)} videos gerados", flush=True)

        # ── Step 7: Convert to 30fps + Upload to MinIO ────────────
        log(f"7/7 Convertendo B-Rolls para 30fps e subindo no MinIO...", flush=True)

        broll_minio_paths: dict[int, str] = {}
        for idx, local_path in broll_local_paths.items():
            if local_path and os.path.exists(local_path):
                converted_path = local_path.replace('.mp4', '_30fps.mp4')
                try:
                    import subprocess
                    subprocess.run(
                        ['ffmpeg', '-y', '-i', local_path,
                         '-r', '30', '-c:v', 'libx264', '-preset', 'fast',
                         '-crf', '23', '-an', converted_path],
                        capture_output=True, timeout=60,
                    )
                    upload_path = converted_path if os.path.exists(converted_path) else local_path
                except Exception:
                    upload_path = local_path

                filename = f"broll_{idx:02d}.mp4"
                minio_path = asset_manager.save_asset_from_file(
                    job_id, "stage2_brolls", filename, upload_path, "video/mp4"
                )
                broll_minio_paths[idx] = minio_path
                log(f"7/7 B-Roll {idx+1}/{len(prompts)} salvo no MinIO", flush=True)

        log(f"CONCLUIDO: {len(broll_minio_paths)}/{len(prompts)} B-Rolls prontos!", flush=True)

        return {
            "word_timestamps": word_timestamps,
            "scenes": scenes,
            "broll_paths": broll_minio_paths,
            "urgent_keywords": urgent_keywords,
            "total_duration": total_duration,
            "prompts_used": prompts,
        }

    except Exception as e:
        # Mark account as failed if we got one
        if account is not None:
            try:
                await account_rotator.mark_account_used(
                    account, success=False, error_message=str(e)
                )
            except Exception:
                pass
        logger.error("[Track B] B-Roll processing failed: {err}", err=e)
        raise

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.debug("[Track B] Cleaned up temp dir: {tmp}", tmp=tmp_dir)
