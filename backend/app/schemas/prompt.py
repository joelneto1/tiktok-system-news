from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PromptOut(BaseModel):
    id: str
    key: str
    name: str
    description: str | None
    content: str
    model_type: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptUpdate(BaseModel):
    content: str


class PromptCreate(BaseModel):
    key: str
    name: str
    description: str | None = None
    content: str
    model_type: str | None = None
