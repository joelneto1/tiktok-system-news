from app.services.openrouter import openrouter_client
from app.utils.logger import logger


class SceneDirector:
    """LLM-based scene director that segments scripts into B-Roll scenes
    with SFX cues."""

    async def direct_scenes(
        self,
        script: str,
        word_timestamps: list[dict],
        total_duration: float,
        system_prompt: str | None = None,
        broll_duration: int = 6,
    ) -> dict:
        """Generate scene directions from a script and its word timestamps.

        Args:
            script: The narration script text.
            word_timestamps: Word-level timestamps from Whisper
                ``[{word, start, end}]``.
            total_duration: Total audio duration in seconds.
            system_prompt: Optional custom system prompt for the LLM.
            broll_duration: Duration of each B-Roll clip in seconds (default 6).

        Returns:
            ``{"scenes": [{start_time, end_time, description, broll_prompt,
            sfx}], "urgent_keywords": [...]}``
        """
        result = await openrouter_client.generate_scene_directions(
            script=script,
            timestamps=word_timestamps,
            system_prompt=system_prompt,
        )

        # Validate and normalise scene durations so they tile the full audio
        raw_scenes = result.get("scenes", [])
        validated_scenes: list[dict] = []
        expected_start = 0.0

        for scene in raw_scenes:
            scene["start_time"] = expected_start
            scene["end_time"] = expected_start + broll_duration

            # Clamp the last scene to the actual audio duration
            if scene["end_time"] > total_duration:
                scene["end_time"] = total_duration

            validated_scenes.append(scene)
            expected_start = scene["end_time"]

            if expected_start >= total_duration:
                break

        # If scenes do not cover the full audio, pad with a generic scene
        while expected_start < total_duration:
            end = min(expected_start + broll_duration, total_duration)
            validated_scenes.append(
                {
                    "start_time": expected_start,
                    "end_time": end,
                    "description": "continuacao da noticia",
                    "broll_prompt": (
                        "Dramatic cinematic news footage, "
                        "4K slow motion, moody lighting"
                    ),
                    "sfx": None,
                }
            )
            expected_start = end

        result["scenes"] = validated_scenes

        keywords = result.get("urgent_keywords", [])
        logger.info(
            "Scene director: {n_scenes} scenes, {n_kw} keywords",
            n_scenes=len(validated_scenes),
            n_kw=len(keywords),
        )

        return result


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
scene_director = SceneDirector()
