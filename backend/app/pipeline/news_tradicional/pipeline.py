import asyncio
from typing import Any

from app.pipeline.base import BasePipeline
from app.pipeline.news_tradicional.stage1_base import generate_script, generate_tts
from app.pipeline.news_tradicional.stage2_track_a import process_avatar
from app.pipeline.news_tradicional.stage2_track_b import process_brolls
from app.pipeline.news_tradicional.stage3_compose import compose_and_render
from app.processing.asset_manager import asset_manager
from app.services.minio_client import minio_client


class NewsTradicionalPipeline(BasePipeline):
    """Full pipeline for News Tradicional video model.

    Stages:
    1a. Script generation  (OpenRouter LLM)
    1b. TTS narration      (GenAIPro)
    2.  FORK:
        - Track A: Avatar  (DreamFace lip-sync + chromakey)
        - Track B: B-Rolls (Whisper + Scene Director + Grok generation)
    3.  Compose & Render   (Remotion)
    """

    async def run(
        self,
        topic: str,
        language: str = "pt-BR",
        voice_id: str = "",
        reference_minio_path: str | None = None,
        db_session: Any = None,
        system_prompts: dict | None = None,
        on_stage_update: Any = None,
        sfx_paths: dict | None = None,
        music_path: str | None = None,
    ) -> str:
        """Execute the complete pipeline. Returns MinIO path to final .mp4."""

        self.logger.info("=== Starting News Tradicional Pipeline ===")
        self.logger.info("Topic: {topic}", topic=topic[:80])
        self.logger.info(
            "Language: {lang}, Voice: {voice}",
            lang=language,
            voice=voice_id or "default",
        )

        # ── STAGE 1a: Script ─────────────────────────────────────────
        # Check if script already exists (resume support)
        existing_script = asset_manager.try_download_text(
            self.job_id, "stage1", "script.txt"
        )
        if existing_script:
            script = existing_script
            self.logger.info("Resuming: script already exists ({n} chars)", n=len(script))
            if on_stage_update:
                await on_stage_update(
                    "stage1_script", "completed", f"Script resumed: {len(script)} chars"
                )
        else:
            if on_stage_update:
                await on_stage_update("stage1_script", "in_progress", "Generating script...")

            script = await self.stage1_script(
                topic,
                language,
                system_prompt=(
                    system_prompts.get("screenwriter") if system_prompts else None
                ),
            )

            # Persist script for traceability
            asset_manager.save_asset(
                self.job_id, "stage1", "script.txt", script.encode(), "text/plain"
            )

            if on_stage_update:
                await on_stage_update(
                    "stage1_script", "completed", f"Script: {len(script)} chars"
                )

        # ── STAGE 1b: TTS ────────────────────────────────────────────
        # Check if TTS already exists (resume support)
        existing_tts = asset_manager.try_get_asset_path(
            self.job_id, "stage1", "tts_audio.mp3"
        )
        if existing_tts:
            audio_path = existing_tts
            self.logger.info("Resuming: TTS already exists at {p}", p=audio_path)
            if on_stage_update:
                await on_stage_update(
                    "stage1_tts", "completed", f"TTS resumed: {audio_path}"
                )
        else:
            if on_stage_update:
                await on_stage_update("stage1_tts", "in_progress", "Generating narration...")

            audio_path, _audio_url, _tts_task_id = await self.stage1_tts(
                script, voice_id
            )

            if on_stage_update:
                await on_stage_update(
                    "stage1_tts", "completed", f"Audio ready: {audio_path}"
                )

        # ── STAGE 2: PARALLEL FORK ───────────────────────────────────
        if on_stage_update:
            await on_stage_update(
                "stage2_avatar", "in_progress", "Processing avatar (DreamFace)..."
            )
            await on_stage_update(
                "stage2_brolls", "in_progress", "Generating B-Rolls (Grok)..."
            )

        # Track A: Avatar (only when a reference video is available)
        track_a_task = None
        if reference_minio_path:
            track_a_task = asyncio.create_task(
                self._run_track_a(
                    reference_minio_path, audio_path, topic,
                    db_session, on_stage_update,
                )
            )

        # Track B: B-Rolls (always runs)
        track_b_task = asyncio.create_task(
            self._run_track_b(
                audio_path, script, language,
                db_session, system_prompts, on_stage_update,
            )
        )

        # Await both tracks (gather with return_exceptions for graceful handling)
        avatar_data: dict | None = None
        broll_data: dict | None = None

        if track_a_task:
            results = await asyncio.gather(
                track_a_task, track_b_task, return_exceptions=True
            )

            # Track A result
            if isinstance(results[0], BaseException):
                self.logger.warning(
                    "Track A (Avatar) failed: {err}. Video will render without avatar.",
                    err=results[0],
                )
                if on_stage_update:
                    await on_stage_update(
                        "stage2_avatar", "failed", str(results[0])[:200]
                    )
            else:
                avatar_data = results[0]

            # Track B result -- B-Rolls are required
            if isinstance(results[1], BaseException):
                self.logger.error(
                    "Track B (B-Rolls) failed: {err}", err=results[1]
                )
                if on_stage_update:
                    await on_stage_update(
                        "stage2_brolls", "failed", str(results[1])[:200]
                    )
                raise results[1]
            else:
                broll_data = results[1]
        else:
            # No avatar requested -- just run B-Rolls
            broll_data = await track_b_task
            if on_stage_update:
                await on_stage_update(
                    "stage2_avatar", "completed", "Skipped (no reference)"
                )

        if on_stage_update:
            await on_stage_update(
                "stage2_brolls",
                "completed",
                f"{len(broll_data['broll_paths'])} B-Rolls ready",
            )

        # ── STAGE 3: Compose & Render ────────────────────────────────
        if on_stage_update:
            await on_stage_update(
                "stage3_render", "in_progress", "Rendering final video..."
            )

        output_path = await self.stage3_compose(
            script=script,
            tts_audio_path=audio_path,
            avatar_data=avatar_data,
            broll_data=broll_data,
            sfx_paths=sfx_paths,
            music_path=music_path,
        )

        if on_stage_update:
            await on_stage_update(
                "stage3_render", "completed", f"Video ready: {output_path}"
            )

        self.logger.success(
            "=== Pipeline Complete: {path} ===", path=output_path
        )
        return output_path

    # ─── Internal helpers ────────────────────────────────────────────

    async def _run_track_a(
        self, reference_path, audio_path, topic, db_session, on_stage_update
    ):
        try:
            result = await process_avatar(
                job_id=self.job_id,
                reference_minio_path=reference_path,
                tts_audio_minio_path=audio_path,
                topic=topic,
                db_session=db_session,
            )
            if on_stage_update:
                await on_stage_update("stage2_avatar", "completed", "Avatar ready")
            return result
        except Exception as exc:
            if on_stage_update:
                await on_stage_update(
                    "stage2_avatar", "failed", str(exc)[:200]
                )
            raise

    async def _run_track_b(
        self, audio_path, script, language, db_session, system_prompts, on_stage_update
    ):
        return await process_brolls(
            job_id=self.job_id,
            tts_audio_minio_path=audio_path,
            script=script,
            language=language,
            db_session=db_session,
            system_prompt_scene_director=(
                system_prompts.get("scene_director") if system_prompts else None
            ),
        )

    # ─── BasePipeline abstract method implementations ────────────────

    async def stage1_script(self, topic, language, system_prompt=None):
        return await generate_script(topic, language, system_prompt)

    async def stage1_tts(self, script, voice_id, **kwargs):
        return await generate_tts(script, voice_id, self.job_id, **kwargs)

    async def stage2_tracks(self, audio_path, script, **kwargs):
        # Not used directly -- run() handles the fork logic internally
        pass

    async def stage3_compose(
        self,
        script=None,
        tts_audio_path=None,
        avatar_data=None,
        broll_data=None,
        sfx_paths=None,
        music_path=None,
        **kwargs,
    ):
        # Build a minimal avatar_data when no avatar is available
        if avatar_data is None:
            avatar_data = {
                "avatar_minio_path": "",
                "duration": broll_data.get("total_duration", 60)
                if broll_data
                else 60,
            }

        return await compose_and_render(
            job_id=self.job_id,
            script=script,
            tts_audio_minio_path=tts_audio_path,
            avatar_data=avatar_data,
            broll_data=broll_data,
            music_path=music_path,
            sfx_paths=sfx_paths,
        )
