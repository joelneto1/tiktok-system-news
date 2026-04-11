from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SettingOut(BaseModel):
    id: str
    key: str
    value: str  # Decrypted if is_encrypted; API keys masked to last 4 chars
    is_encrypted: bool
    category: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class SettingUpdate(BaseModel):
    value: str


class SettingBulkUpdate(BaseModel):
    settings: dict[str, str]  # key -> value pairs
