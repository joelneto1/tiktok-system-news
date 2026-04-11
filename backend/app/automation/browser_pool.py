import asyncio

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from app.config import settings
from app.utils.logger import logger


class BrowserPool:
    """Manages Playwright browser instances and contexts.

    Supports two modes:
    - Local: launches a local Chromium browser
    - CDP: connects to an existing Chromium via Chrome DevTools Protocol (noVNC container)
    """

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()
        self._contexts: dict[str, BrowserContext] = {}  # account_id -> context

    async def _ensure_browser(self) -> Browser:
        """Lazily initialize Playwright and connect/launch browser."""
        async with self._lock:
            if self._browser and self._browser.is_connected():
                return self._browser

            self._playwright = await async_playwright().start()

            cdp_url = settings.CDP_URL  # e.g. http://localhost:9222
            try:
                # Try CDP connection first (noVNC container)
                self._browser = await self._playwright.chromium.connect_over_cdp(
                    cdp_url
                )
                logger.info(f"Connected to browser via CDP: {cdp_url}")
            except Exception as e:
                logger.warning(f"CDP connection failed ({e}), launching local browser")
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                logger.info("Launched local headless Chromium")

            return self._browser

    async def get_context(
        self,
        account_id: str,
        cookies: list[dict] | None = None,
        proxy: dict | None = None,
    ) -> BrowserContext:
        """Get or create a browser context for an account.

        Args:
            account_id: Unique ID for this account's context.
            cookies: List of cookie dicts to inject.
            proxy: Proxy config ``{"server": "http://...", "username": "...", "password": "..."}``.

        Returns:
            BrowserContext ready for automation.
        """
        # Return existing context if available and still connected
        if account_id in self._contexts:
            ctx = self._contexts[account_id]
            try:
                # Test if context is still alive
                if ctx.pages:
                    await ctx.pages[0].title()
                return ctx
            except Exception:
                # Context died, remove it
                del self._contexts[account_id]

        browser = await self._ensure_browser()

        # Create new context with optional proxy
        ctx_options: dict = {
            "viewport": {"width": 1280, "height": 720},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        if proxy:
            ctx_options["proxy"] = proxy

        ctx = await browser.new_context(**ctx_options)

        # Inject cookies if provided
        if cookies:
            await ctx.add_cookies(cookies)
            logger.debug(f"Injected {len(cookies)} cookies for account {account_id}")

        self._contexts[account_id] = ctx
        return ctx

    async def get_page(self, account_id: str, **kwargs) -> Page:
        """Get a new page in the account's context."""
        ctx = await self.get_context(account_id, **kwargs)
        page = await ctx.new_page()
        return page

    async def capture_cookies(self, account_id: str) -> list[dict]:
        """Capture all cookies from an account's context."""
        if account_id not in self._contexts:
            return []
        ctx = self._contexts[account_id]
        cookies = await ctx.cookies()
        logger.info(f"Captured {len(cookies)} cookies from account {account_id}")
        return cookies

    async def release_context(self, account_id: str) -> None:
        """Close and release a context."""
        if account_id in self._contexts:
            try:
                await self._contexts[account_id].close()
            except Exception:
                pass
            del self._contexts[account_id]

    async def close_all(self) -> None:
        """Cleanup all contexts and browser."""
        for aid in list(self._contexts.keys()):
            await self.release_context(aid)
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser pool closed")


# Singleton
browser_pool = BrowserPool()
