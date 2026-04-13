import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.connection_account import ConnectionAccount
from app.models.user import User
from app.schemas.connection import AccountCreate, AccountOut, AccountUpdate
from app.utils.activity_log import log_activity
from app.utils.crypto import encrypt_value


def _extract_cookie_expiry(cookies_json: str) -> datetime | None:
    """Extract the earliest auth cookie expiration from a cookies JSON string."""
    try:
        cookies = json.loads(cookies_json)
        if not isinstance(cookies, list):
            return None
        # Look for auth cookies (sso, sso-rw, token)
        auth_names = {"sso", "sso-rw", "token"}
        min_exp = None
        for c in cookies:
            name = c.get("name", "")
            exp = c.get("expirationDate", 0)
            if name in auth_names and exp:
                exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
                if min_exp is None or exp_dt < min_exp:
                    min_exp = exp_dt
        return min_exp
    except Exception:
        return None

router = APIRouter(prefix="/connections", tags=["connections"])


def _account_to_out(account: ConnectionAccount) -> AccountOut:
    return AccountOut(
        id=str(account.id),
        service=account.service,
        account_name=account.account_name,
        account_type=account.account_type,
        proxy_url=account.proxy_url,
        is_active=account.is_active,
        credits=account.credits,
        cookie_expires_at=account.cookie_expires_at,
        token_expires_at=account.token_expires_at,
        status=account.status,
        last_verified_at=account.last_verified_at,
        error_message=account.error_message,
        created_at=account.created_at,
    )


@router.get("", response_model=list[AccountOut])
async def list_accounts(
    service: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all connection accounts, optionally filtered by service."""
    query = select(ConnectionAccount)
    if service:
        query = query.where(ConnectionAccount.service == service)
    query = query.order_by(ConnectionAccount.service, ConnectionAccount.account_name)

    result = await db.execute(query)
    accounts = result.scalars().all()
    return [_account_to_out(a) for a in accounts]


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def add_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new connection account."""
    # Encrypt cookies if provided
    cookies_encrypted = encrypt_value(data.cookies_json) if data.cookies_json else None
    cookie_exp = _extract_cookie_expiry(data.cookies_json) if data.cookies_json else None

    account = ConnectionAccount(
        service=data.service,
        account_name=data.account_name,
        account_type=data.account_type,
        cookies_json=cookies_encrypted,
        proxy_url=data.proxy_url,
        cookie_expires_at=cookie_exp,
        status="active" if data.cookies_json else "disconnected",
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    await log_activity(db, "SUCCESS", f"Conta adicionada: {data.service} - {data.account_name}", stage="connections")
    return _account_to_out(account)


async def _get_account_or_404(
    account_id: str, db: AsyncSession
) -> ConnectionAccount:
    """Fetch a ConnectionAccount by ID or raise 404."""
    try:
        uid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    result = await db.execute(
        select(ConnectionAccount).where(ConnectionAccount.id == uid)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    return account


@router.patch("/{account_id}", response_model=AccountOut)
async def update_account(
    account_id: str,
    data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Partially update a connection account."""
    account = await _get_account_or_404(account_id, db)

    if data.is_active is not None:
        account.is_active = data.is_active
    if data.cookies_json is not None:
        account.cookies_json = encrypt_value(data.cookies_json)
        account.cookie_expires_at = _extract_cookie_expiry(data.cookies_json)
    if data.proxy_url is not None:
        account.proxy_url = data.proxy_url
    if data.account_type is not None:
        account.account_type = data.account_type

    await db.flush()
    await db.refresh(account)
    return _account_to_out(account)


@router.patch("/{account_id}/toggle", response_model=AccountOut)
async def toggle_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle is_active on/off for a connection account."""
    account = await _get_account_or_404(account_id, db)
    account.is_active = not account.is_active
    await db.flush()
    await db.refresh(account)
    await log_activity(db, "INFO", f"Conta {'ativada' if account.is_active else 'desativada'}: {account.account_name}", stage="connections")
    return _account_to_out(account)


@router.post("/{account_id}/refresh")
async def refresh_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Refresh / verify a connection account.

    Placeholder: will verify cookies via Playwright in Phase 5.
    For now just updates last_verified_at.
    """
    account = await _get_account_or_404(account_id, db)
    account.last_verified_at = datetime.now(timezone.utc)
    account.status = "connected"
    account.error_message = None
    await db.flush()
    await db.refresh(account)
    return {"status": "ok", "last_verified_at": account.last_verified_at.isoformat()}


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a connection account."""
    account = await _get_account_or_404(account_id, db)
    account_name = account.account_name
    await db.delete(account)
    await db.flush()
    await log_activity(db, "WARNING", f"Conta excluida: {account_name}", stage="connections")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
