from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReferenceOut(BaseModel):
    id: str
    name: str
    original_filename: str
    minio_path: str
    thumbnail_path: str | None
    duration: float | None
    file_size: int | None
    mime_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReferenceRename(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ReferenceListResponse(BaseModel):
    references: list[ReferenceOut]
    total: int
