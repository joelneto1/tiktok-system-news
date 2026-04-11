from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountOut(BaseModel):
    id: str
    service: str  # "dreamface" or "grok"
    account_name: str
    account_type: str | None
    proxy_url: str | None
    is_active: bool
    credits: int
    cookie_expires_at: datetime | None
    token_expires_at: datetime | None
    status: str
    last_verified_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountCreate(BaseModel):
    service: str = Field(pattern=r"^(dreamface|grok)$")
    account_name: str
    account_type: str | None = None
    cookies_json: str | None = None
    proxy_url: str | None = None


class AccountUpdate(BaseModel):
    is_active: bool | None = None
    cookies_json: str | None = None
    proxy_url: str | None = None
    account_type: str | None = None
