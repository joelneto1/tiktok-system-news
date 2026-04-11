import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
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
        """Parse cookies JSON from an account record."""
        if not account.cookies_json:
            return []
        try:
            cookies = json.loads(account.cookies_json)
            if isinstance(cookies, list):
                return cookies
            return []
        except json.JSONDecodeError:
            logger.error(
                f"Invalid cookies JSON for account {account.account_name}"
            )
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
        async with async_session_factory() as db:
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
