from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LogOut(BaseModel):
    id: str
    video_id: str | None
    job_id: str | None
    stage: str | None
    level: str
    message: str
    metadata_json: dict | None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class LogListResponse(BaseModel):
    logs: list[LogOut]
    total: int
    page: int
    page_size: int
