from app.services.genaipro import genaipro_client
from app.services.minio_client import minio_client
from app.services.openrouter import openrouter_client
from app.utils.logger import logger


async def generate_script(
    topic: str,
    language: str = "pt-BR",
    system_prompt: str | None = None,
) -> str:
    """Stage 1a -- Generate a narration script using the LLM."""
    logger.info("Generating script for topic: {topic}...", topic=topic[:50])
    script = await openrouter_client.generate_script(topic, language, system_prompt)
    logger.success("Script generated: {n} chars", n=len(script))
    return script


DEFAULT_VOICE_ID = "6ZseIH4NYfWg7mfPFOvh"

async def generate_tts(
    script: str,
    voice_id: str,
    job_id: str,
    model_id: str = "eleven_multilingual_v2",
    **tts_kwargs,
) -> tuple[str, str, str]:
    """Stage 1b -- Convert a script to speech using GenAIPro TTS.

    Returns:
        ``(minio_audio_path, audio_url, tts_task_id)``
    """
    logger.info("Creating TTS task for {n} chars...", n=len(script))

    # Create TTS task (use default voice if none provided)
    task_id = await genaipro_client.create_tts_task(
        text=script,
        voice_id=voice_id or DEFAULT_VOICE_ID,
        model_id=model_id,
        **tts_kwargs,
    )

    # Wait for completion via polling (more reliable than WebSocket)
    task = await genaipro_client.poll_task(task_id)

    audio_url: str = task.get("result", "")
    if not audio_url:
        raise RuntimeError(f"TTS task {task_id} completed but returned no audio URL")

    # Download the audio and persist to MinIO
    audio_bytes = await genaipro_client.download_audio(audio_url)

    minio_path = f"jobs/{job_id}/stage1/tts_audio.mp3"
    minio_client.upload_file(minio_path, audio_bytes, "audio/mpeg")
    logger.success("TTS audio saved to MinIO: {path}", path=minio_path)

    return minio_path, audio_url, task_id
