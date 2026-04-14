import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.database as db_module
from app.models.connection_account import ConnectionAccount
from app.utils.logger import logger


class AccountRotator:
    """Manages round-robin selection of active accounts for DreamFace/Grok."""

    def __init__(self) -> None:
        self._last_used: dict[str, int] = {}  # service -> last used index

    async def get_next_account(
        self,
        service: str,
        db: AsyncSession,
    ) -> ConnectionAccount | None:
        """Get the next available active account for a service.

        Selection criteria:
        1. ``is_active = True`` (toggle ON)
        2. ``status = 'active'`` (not expired/disconnected)
        3. Round-robin rotation among eligible accounts

        Returns ``None`` if no accounts available.
        """
        result = await db.execute(
            select(ConnectionAccount)
            .where(
                ConnectionAccount.service == service,
                ConnectionAccount.is_active == True,  # noqa: E712
                ConnectionAccount.status == "active",
            )
            .order_by(ConnectionAccount.created_at)
        )
        accounts = list(result.scalars().all())

        if not accounts:
            logger.warning(f"No active {service} accounts available")
            return None

        # Round-robin: pick next after last used
        last_idx = self._last_used.get(service, -1)
        next_idx = (last_idx + 1) % len(accounts)
        self._last_used[service] = next_idx

        account = accounts[next_idx]
        logger.info(
            f"Selected {service} account: {account.account_name} "
            f"(#{next_idx + 1}/{len(accounts)})"
        )
        return account

    async def get_account_cookies(self, account: ConnectionAccount) -> list[dict]:
        """Parse cookies from an account record. Handles encrypted + raw formats."""
        if not account.cookies_json:
            return []

        raw = account.cookies_json

        # Try to decrypt if encrypted (Fernet tokens start with 'gAAAAA')
        if raw.startswith("gAAAAA"):
            try:
                from app.utils.crypto import decrypt_value
                raw = decrypt_value(raw)
            except Exception as e:
                logger.error(f"Failed to decrypt cookies for {account.account_name}: {e}")
                return []

        # Try JSON format
        try:
            parsed = json.loads(raw)

            # JSON array = Playwright cookie format
            if isinstance(parsed, list):
                return parsed

            # JSON object = localStorage format (DreamFace uses this)
            if isinstance(parsed, dict):
                # Convert to list of {name, value} items for localStorage injection
                items = [
                    {"name": k, "value": v if isinstance(v, str) else json.dumps(v)}
                    for k, v in parsed.items()
                ]
                logger.debug(f"Parsed {len(items)} localStorage items for {account.account_name}")
                return items
        except json.JSONDecodeError:
            pass

        # Fall back to cookie string format: "name1=value1; name2=value2"
        cookie_list = []
        domain = ".dreamfaceapp.com" if account.service == "dreamface" else ".grok.com" if account.service == "grok" else ".example.com"
        for pair in raw.split(";"):
            pair = pair.strip()
            if "=" in pair:
                name, value = pair.split("=", 1)
                cookie_list.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": domain,
                    "path": "/",
                })
        if cookie_list:
            logger.debug(f"Parsed {len(cookie_list)} cookies from string for {account.account_name}")
            return cookie_list

        logger.error(f"Could not parse cookies for {account.account_name}")
        return []

    async def get_account_proxy(self, account: ConnectionAccount) -> dict | None:
        """Parse proxy URL from account into Playwright proxy config.

        Supported formats:
        - ``username:password@host:port``
        - ``host:port``
        - ``http://host:port``
        """
        if not account.proxy_url:
            return None

        proxy_url = account.proxy_url.strip()

        if "@" in proxy_url:
            auth, server = proxy_url.rsplit("@", 1)
            if ":" in auth:
                username, password = auth.split(":", 1)
                return {
                    "server": f"http://{server}",
                    "username": username,
                    "password": password,
                }
            return {"server": f"http://{server}"}

        if not proxy_url.startswith("http"):
            return {"server": f"http://{proxy_url}"}

        return {"server": proxy_url}

    async def mark_account_used(
        self,
        account: ConnectionAccount,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """Update account after use (credits, status, etc.)."""
        async with db_module.async_session_factory() as db:
            from sqlalchemy import update
            stmt = update(ConnectionAccount).where(
                ConnectionAccount.id == account.id
            ).values(
                last_verified_at=datetime.now(timezone.utc),
                error_message=error_message if not success else None,
            )
            await db.execute(stmt)
            await db.commit()

    async def mark_account_expired(
        self,
        account: ConnectionAccount,
        db: AsyncSession,
    ) -> None:
        """Mark account as expired (cookies no longer valid)."""
        account.status = "expired"
        account.error_message = "Cookies expired"
        await db.flush()
        logger.warning(f"Account {account.account_name} marked as expired")


# Singleton
account_rotator = AccountRotator()
