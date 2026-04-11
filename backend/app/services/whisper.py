from openai import AsyncOpenAI

from app.config import settings
from app.utils.logger import logger


class WhisperClient:
    """Client for OpenAI Whisper API (speech-to-text with word timestamps)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        response_format: str = "verbose_json",
    ) -> dict:
        """Transcribe an audio file with word-level timestamps.

        Args:
            audio_path: Local filesystem path to the audio file.
            language: BCP-47 language tag (e.g. ``"pt-BR"``).  Only the first
                two characters are sent to Whisper.
            response_format: Whisper response format (default ``verbose_json``).

        Returns:
            A dict containing at least ``text``, ``words``, and ``segments``.
        """
        lang_code = language[:2] if language else None

        with open(audio_path, "rb") as audio_file:
            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format=response_format,
                timestamp_granularities=["word", "segment"],
                language=lang_code,
            )

        result: dict = (
            transcript.model_dump()
            if hasattr(transcript, "model_dump")
            else dict(transcript)
        )

        words = result.get("words", [])
        duration = result.get("duration", 0)
        logger.info(
            "Whisper transcription: {n} words, duration: {dur:.1f}s",
            n=len(words),
            dur=duration,
        )
        return result

    async def transcribe_to_word_timestamps(
        self,
        audio_path: str,
        language: str | None = None,
    ) -> list[dict]:
        """Convenience method returning only the word-level timestamps.

        Returns:
            ``[{"word": "hello", "start": 0.0, "end": 0.5}, ...]``
        """
        result = await self.transcribe(audio_path, language)
        return result.get("words", [])


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
whisper_client = WhisperClient()
