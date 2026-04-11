from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.video import VideoOut


class PipelineStartRequest(BaseModel):
    topic: str = Field(min_length=1)
    language: str = "pt-BR"
    model_type: str = "news_tradicional"
    reference_id: str | None = None
    audio_id: str | None = None
    voice_id: str | None = None


class StageInfo(BaseModel):
    name: str
    description: str
    status: str  # pending, in_progress, completed, failed
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PipelineStatusResponse(BaseModel):
    video: VideoOut
    stages: list[StageInfo]
