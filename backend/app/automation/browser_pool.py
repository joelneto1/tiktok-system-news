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

    Each call creates a fresh Playwright instance to avoid event loop conflicts
    when running inside Celery (which creates a new loop per task).
    """

    async def get_context(
        self,
        account_id: str,
        cookies: list[dict] | None = None,
        proxy: dict | None = None,
    ) -> tuple[Playwright, Browser, BrowserContext]:
        """Create a fresh browser context for an account.

        Returns a tuple of (playwright, browser, context) — caller must close all three
        when done by calling release().
        """
        pw = await async_playwright().start()

        cdp_url = settings.CDP_URL
        browser = None

        if cdp_url:
            try:
                browser = await pw.chromium.connect_over_cdp(cdp_url, timeout=5000)
                logger.info(f"Connected to browser via CDP: {cdp_url}")
            except Exception as e:
                logger.warning(f"CDP connection failed ({e}), falling back to headless")
                browser = None

        if browser is None:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                ],
            )
            logger.info("Launched local headless Chromium")

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

        if cookies:
            await ctx.add_cookies(cookies)
            logger.debug(f"Injected {len(cookies)} cookies for account {account_id}")

        return pw, browser, ctx

    async def get_page(
        self,
        account_id: str,
        cookies: list[dict] | None = None,
        proxy: dict | None = None,
    ) -> tuple[Playwright, Browser, BrowserContext, Page]:
        """Get a new page with fresh browser. Returns (pw, browser, ctx, page)."""
        pw, browser, ctx = await self.get_context(account_id, cookies=cookies, proxy=proxy)
        page = await ctx.new_page()
        return pw, browser, ctx, page

    async def release(
        self,
        pw: Playwright,
        browser: Browser,
        ctx: BrowserContext,
    ) -> None:
        """Close context, browser and playwright instance."""
        try:
            await ctx.close()
        except Exception:
            pass
        try:
            await browser.close()
        except Exception:
            pass
        try:
            await pw.stop()
        except Exception:
            pass
        logger.debug("Browser resources released")

    async def capture_cookies(self, ctx: BrowserContext) -> list[dict]:
        """Capture all cookies from a context."""
        cookies = await ctx.cookies()
        logger.info(f"Captured {len(cookies)} cookies")
        return cookies


# Singleton
browser_pool = BrowserPool()
