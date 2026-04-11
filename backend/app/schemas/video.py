from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VideoOut(BaseModel):
    id: str
    topic: str
    language: str
    model_type: str
    status: str
    current_stage: str | None
    progress_percent: int
    total_stages: int
    completed_stages: int
    attempts: int
    script: str | None
    output_url: str | None
    error_message: str | None
    reference_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoListResponse(BaseModel):
    videos: list[VideoOut]
    total: int
    page: int
    page_size: int
