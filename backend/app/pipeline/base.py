from abc import ABC, abstractmethod

from app.utils.logger import logger


class BasePipeline(ABC):
    """Abstract base class for all video generation pipelines."""

    def __init__(self, job_id: str, video_id: str):
        self.job_id = job_id
        self.video_id = video_id
        self.logger = logger.bind(job_id=job_id)

    @abstractmethod
    async def run(self) -> str:
        """Execute the full pipeline.  Returns the output MinIO path."""
        ...

    @abstractmethod
    async def stage1_script(
        self, topic: str, language: str, system_prompt: str | None = None
    ) -> str:
        """Generate the narration script.  Returns script text."""
        ...

    @abstractmethod
    async def stage1_tts(self, script: str, voice_id: str, **kwargs) -> tuple[str, str]:
        """Generate TTS audio.  Returns ``(audio_minio_path, tts_task_id)``."""
        ...

    @abstractmethod
    async def stage2_tracks(self, audio_path: str, script: str, **kwargs) -> dict:
        """Execute parallel processing tracks.  Returns an assets dict."""
        ...

    @abstractmethod
    async def stage3_compose(self, assets: dict) -> str:
        """Compose the final video.  Returns the output MinIO path."""
        ...
