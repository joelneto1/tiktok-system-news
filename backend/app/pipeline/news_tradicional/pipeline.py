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
        avatar_data: dict | None = None
        broll_data: dict | None = None

        # ── Resume check: Avatar ──
        existing_avatar_raw = asset_manager.try_get_asset_path(
            self.job_id, "stage2_avatar", "avatar_raw.mp4"
        )
        existing_avatar_webm = asset_manager.try_get_asset_path(
            self.job_id, "stage2_avatar", "avatar_alpha.webm"
        )

        if existing_avatar_raw and existing_avatar_webm:
            self.logger.info(
                "Resuming: avatar already exists in MinIO, skipping DreamFace"
            )
            # Reconstruct avatar_data from existing assets
            from app.processing.ffmpeg import ffmpeg_processor
            import tempfile, os
            # Download webm to get duration
            try:
                webm_data = minio_client.download_file(existing_avatar_webm)
                tmp_webm = tempfile.mktemp(suffix=".webm")
                with open(tmp_webm, "wb") as f:
                    f.write(webm_data)
                duration = await ffmpeg_processor.get_duration(tmp_webm)
                os.unlink(tmp_webm)
            except Exception:
                duration = 60.0  # fallback
            avatar_data = {
                "avatar_minio_path": existing_avatar_webm,
                "avatar_raw_path": existing_avatar_raw,
                "duration": duration,
            }
            if on_stage_update:
                await on_stage_update(
                    "stage2_avatar", "completed", "Avatar resumed from MinIO"
                )

        # ── Resume check: B-Rolls ──
        existing_scenes_json = asset_manager.try_download_text(
            self.job_id, "stage2_brolls", "scenes.json"
        )
        if existing_scenes_json:
            import json
            try:
                scene_data = json.loads(existing_scenes_json)
                scenes = scene_data.get("scenes", [])
                # Check if actual broll video files exist
                broll_paths = {}
                for idx in range(len(scenes)):
                    bp = asset_manager.try_get_asset_path(
                        self.job_id, "stage2_brolls", f"broll_{idx:02d}.mp4"
                    )
                    if bp:
                        broll_paths[idx] = bp
                if broll_paths:
                    self.logger.info(
                        "Resuming: {n}/{t} B-Rolls already in MinIO",
                        n=len(broll_paths), t=len(scenes),
                    )
            except Exception:
                broll_paths = {}
                scene_data = None
        else:
            broll_paths = {}
            scene_data = None

        # Determine what still needs to run
        need_avatar = avatar_data is None and reference_minio_path
        need_brolls = not broll_paths  # No existing brolls found

        if need_avatar:
            if on_stage_update:
                await on_stage_update(
                    "stage2_avatar", "in_progress", "Processing avatar (DreamFace)..."
                )
        if need_brolls:
            if on_stage_update:
                await on_stage_update(
                    "stage2_brolls", "in_progress", "Generating B-Rolls (Grok)..."
                )
        elif on_stage_update:
            await on_stage_update(
                "stage2_brolls", "completed",
                f"B-Rolls resumed: {len(broll_paths)} from MinIO"
            )

        # Launch only the tracks that are needed
        track_a_task = None
        track_b_task = None

        if need_avatar:
            track_a_task = asyncio.create_task(
                self._run_track_a(
                    reference_minio_path, audio_path, topic,
                    db_session, on_stage_update,
                )
            )

        if need_brolls:
            track_b_task = asyncio.create_task(
                self._run_track_b(
                    audio_path, script, language,
                    db_session, system_prompts, on_stage_update,
                )
            )

        # Await whatever is running
        tasks = {}
        if track_a_task:
            tasks["avatar"] = track_a_task
        if track_b_task:
            tasks["brolls"] = track_b_task

        if tasks:
            results = await asyncio.gather(
                *tasks.values(), return_exceptions=True
            )
            task_keys = list(tasks.keys())

            for i, key in enumerate(task_keys):
                if isinstance(results[i], BaseException):
                    if key == "avatar":
                        self.logger.warning(
                            "Track A (Avatar) failed: {err}.",
                            err=results[i],
                        )
                        if on_stage_update:
                            await on_stage_update(
                                "stage2_avatar", "failed", str(results[i])[:200]
                            )
                    elif key == "brolls":
                        self.logger.error(
                            "Track B (B-Rolls) failed: {err}", err=results[i]
                        )
                        if on_stage_update:
                            await on_stage_update(
                                "stage2_brolls", "failed", str(results[i])[:200]
                            )
                        raise results[i]
                else:
                    if key == "avatar":
                        avatar_data = results[i]
                    elif key == "brolls":
                        broll_data = results[i]

        # If B-Rolls were resumed, reconstruct broll_data
        if broll_data is None and broll_paths and scene_data:
            # Load word_timestamps
            existing_ts = asset_manager.try_download_text(
                self.job_id, "stage2_brolls", "word_timestamps.json"
            )
            import json
            word_timestamps = json.loads(existing_ts) if existing_ts else []

            # Get audio duration
            from app.processing.ffmpeg import ffmpeg_processor
            import tempfile, os
            try:
                audio_data = minio_client.download_file(audio_path)
                tmp_audio = tempfile.mktemp(suffix=".mp3")
                with open(tmp_audio, "wb") as f:
                    f.write(audio_data)
                total_dur = await ffmpeg_processor.get_duration(tmp_audio)
                os.unlink(tmp_audio)
            except Exception:
                total_dur = 60.0

            broll_data = {
                "word_timestamps": word_timestamps,
                "scenes": scene_data.get("scenes", []),
                "broll_paths": broll_paths,
                "urgent_keywords": scene_data.get("urgent_keywords", []),
                "total_duration": total_dur,
                "prompts_used": [
                    s.get("broll_prompt", "") for s in scene_data.get("scenes", [])
                ],
            }

        if not reference_minio_path and avatar_data is None:
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
            topic=topic,
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
        topic="",
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
            topic=topic,
        )
