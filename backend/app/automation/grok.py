"""Grok text-to-video automation via Playwright.

Mapped from real Grok UI at grok.com/imagine:

Selectors (mapped from console inspection):
- Prompt input: div.tiptap.ProseMirror (contenteditable)
- "Video" mode: button with text "Vídeo"
- "720p" resolution: button with text "720p"
- "9:16" aspect: button[aria-label="Aspecto de proporção"] with text "9:16"
- "6s" duration: button with text "6s"
- Submit: button[type="submit"][aria-label="submeter"]
- Progress: text "Gerando XX%" visible during generation
- Result video: video element with src containing "assets.grok.com"
- Download: button[aria-label="Baixar"]

CDN URL pattern:
  https://assets.grok.com/users/{user_id}/generated/{post_id}/generated_video.mp4
"""

import asyncio
import os
import tempfile

import httpx
from playwright.async_api import Page, BrowserContext, TimeoutError as PlaywrightTimeout

from app.automation.browser_pool import browser_pool
from app.utils.logger import logger
from app.utils.retry import retry_async
from app.config import settings


class GrokAutomation:
    """Automates Grok text-to-video generation with batch tab management."""

    BASE_URL = "https://grok.com"
    IMAGINE_URL = "https://grok.com/imagine"

    def __init__(self):
        self.logger = logger

    async def batch_generate(
        self,
        prompts: list[str],
        account_id: str,
        cookies: list[dict],
        proxy: dict | None = None,
        batch_size: int | None = None,
        max_retries: int = 2,
        timeout_per_video: float = 300,
        on_progress=None,
    ) -> dict[int, str]:
        """Generate multiple videos from prompts in batched parallel tabs.

        Args:
            prompts: List of text-to-video prompts
            account_id: Account ID for browser context
            cookies: Auth cookies
            proxy: Optional proxy
            batch_size: Tabs per batch (default from settings)
            max_retries: Max retries for failed tabs
            timeout_per_video: Timeout per video in seconds
            on_progress: Callback(completed, total, message)

        Returns:
            Dict mapping prompt_index → local_file_path for successful generations
        """
        if batch_size is None:
            batch_size = getattr(settings, 'BROLL_BATCH_SIZE', 10)

        total = len(prompts)
        results: dict[int, str] = {}
        failed_indices: list[int] = list(range(total))

        self.logger.info(f"Grok: Starting batch generation of {total} videos (batch_size={batch_size})")

        for retry_round in range(max_retries + 1):
            if not failed_indices:
                break

            if retry_round > 0:
                self.logger.info(f"Grok: Retry round {retry_round} for {len(failed_indices)} failed videos")

            # Process in batches
            batches = [
                failed_indices[i:i + batch_size]
                for i in range(0, len(failed_indices), batch_size)
            ]

            new_failed = []

            for batch_num, batch_indices in enumerate(batches):
                self.logger.info(f"Grok: Batch {batch_num + 1}/{len(batches)} ({len(batch_indices)} tabs)")

                batch_results = await self._process_batch(
                    prompts=[(idx, prompts[idx]) for idx in batch_indices],
                    account_id=account_id,
                    cookies=cookies,
                    proxy=proxy,
                    timeout=timeout_per_video,
                )

                for idx, path in batch_results.items():
                    if path:
                        results[idx] = path
                    else:
                        new_failed.append(idx)

                completed = len(results)
                if on_progress:
                    on_progress(completed, total, f"Batch {batch_num + 1}/{len(batches)} done")

                self.logger.info(f"Grok: Progress: {completed}/{total} completed, {len(new_failed)} failed")

            failed_indices = new_failed

        if failed_indices:
            self.logger.warning(f"Grok: {len(failed_indices)} videos failed after all retries")

        self.logger.success(f"Grok: Batch complete: {len(results)}/{total} successful")
        return results

    async def _process_batch(
        self,
        prompts: list[tuple[int, str]],
        account_id: str,
        cookies: list[dict],
        proxy: dict | None,
        timeout: float,
    ) -> dict[int, str | None]:
        """Process a single batch of prompts in parallel tabs."""
        pw, browser, ctx = await browser_pool.get_context(account_id, cookies=cookies, proxy=proxy)
        results: dict[int, str | None] = {}
        pages: dict[int, Page] = {}

        try:
            # Open tabs and submit prompts
            for idx, prompt in prompts:
                try:
                    page = await ctx.new_page()
                    pages[idx] = page

                    # Navigate to Grok Imagine
                    await page.goto(self.IMAGINE_URL, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(2000)

                    # Dismiss cookie banner (blocks submit button)
                    await self._dismiss_cookie_banner(page)

                    # Configure: Video mode, 720p, 9:16
                    await self._configure_video_settings(page)

                    # Insert prompt
                    await self._insert_prompt(page, prompt)

                    # Submit
                    await self._submit_prompt(page)

                    self.logger.debug(f"Grok tab {idx}: Submitted prompt")

                except Exception as e:
                    self.logger.error(f"Grok tab {idx}: Setup failed: {e}")
                    results[idx] = None
                    if idx in pages:
                        try:
                            await pages[idx].close()
                        except Exception:
                            pass
                        del pages[idx]

            # Wait for all to complete and download
            for idx, page in list(pages.items()):
                try:
                    video_url = await self._wait_for_video(page, timeout)
                    if video_url:
                        local_path = await self._download_video(video_url, idx)
                        results[idx] = local_path
                    else:
                        results[idx] = None
                except Exception as e:
                    self.logger.error(f"Grok tab {idx}: Failed: {e}")
                    results[idx] = None

        finally:
            for idx, page in pages.items():
                try:
                    await page.close()
                except Exception:
                    pass
            await browser_pool.release(pw, browser, ctx)

        return results

    async def _dismiss_cookie_banner(self, page: Page):
        """Remove cookie consent banner that blocks the submit button."""
        try:
            await page.evaluate('document.querySelector("[data-cookie-banner]")?.remove()')
            self.logger.debug("Grok: Cookie banner removed")
        except Exception:
            pass

    async def _configure_video_settings(self, page: Page):
        """Configure Grok for video generation: Video mode, 720p, 9:16 aspect."""

        # Click "Video" mode button
        try:
            video_btn = page.get_by_text("Vídeo", exact=True)
            if await video_btn.is_visible(timeout=3000):
                await video_btn.click()
                await page.wait_for_timeout(500)
                self.logger.debug("Grok: Video mode selected")
        except (PlaywrightTimeout, Exception):
            # Try English fallback
            try:
                video_btn = page.get_by_text("Video", exact=True)
                await video_btn.click()
                await page.wait_for_timeout(500)
            except Exception:
                pass

        # Click "720p" resolution
        try:
            res_btn = page.get_by_text("720p", exact=True)
            if await res_btn.is_visible(timeout=2000):
                await res_btn.click()
                await page.wait_for_timeout(500)
                self.logger.debug("Grok: 720p selected")
        except (PlaywrightTimeout, Exception):
            pass

        # Click "9:16" aspect ratio
        try:
            aspect_btn = page.locator('button[aria-label="Aspecto de proporção"]')
            if not await aspect_btn.is_visible(timeout=2000):
                # Try English label
                aspect_btn = page.locator('button[aria-label="Aspect ratio"]')

            if await aspect_btn.is_visible(timeout=2000):
                # Check if already 9:16
                text = await aspect_btn.inner_text()
                if "9:16" not in text:
                    await aspect_btn.click()
                    await page.wait_for_timeout(500)
                    # Select 9:16 from dropdown if needed
                    try:
                        option = page.get_by_text("9:16", exact=True)
                        await option.click()
                        await page.wait_for_timeout(500)
                    except Exception:
                        pass
                self.logger.debug("Grok: 9:16 aspect selected")
        except (PlaywrightTimeout, Exception):
            pass

    async def _insert_prompt(self, page: Page, prompt: str):
        """Insert the text-to-video prompt into the ProseMirror editor."""
        # The prompt input is a ProseMirror contenteditable div
        editor = page.locator("div.tiptap.ProseMirror")

        try:
            await editor.click()
            await page.wait_for_timeout(300)

            # Clear existing content and type new prompt
            await editor.fill("")
            await page.wait_for_timeout(200)
            await editor.press_sequentially(prompt[:500], delay=10)  # Limit to 500 chars

            self.logger.debug(f"Grok: Prompt inserted ({len(prompt)} chars)")
        except Exception:
            # Fallback: try typing directly
            await page.keyboard.type(prompt[:500], delay=10)

    async def _submit_prompt(self, page: Page):
        """Click the submit button to start generation."""
        try:
            # Primary: submit button with aria-label
            submit_btn = page.locator('button[type="submit"][aria-label="submeter"]')
            if await submit_btn.is_visible(timeout=3000):
                await submit_btn.click()
                self.logger.debug("Grok: Submit clicked (aria-label)")
                await page.wait_for_timeout(2000)
                return
        except (PlaywrightTimeout, Exception):
            pass

        try:
            # English fallback
            submit_btn = page.locator('button[type="submit"][aria-label="submit"]')
            if await submit_btn.is_visible(timeout=2000):
                await submit_btn.click()
                self.logger.debug("Grok: Submit clicked (English)")
                await page.wait_for_timeout(2000)
                return
        except (PlaywrightTimeout, Exception):
            pass

        # Last resort: press Enter
        await page.keyboard.press("Enter")
        self.logger.debug("Grok: Used Enter key fallback")
        await page.wait_for_timeout(2000)

    async def _wait_for_video(self, page: Page, timeout: float = 300) -> str | None:
        """Wait for video generation to complete and return the CDN URL.

        Monitors for:
        - "Gerando XX%" progress text to disappear
        - <video> element with src containing "assets.grok.com" to appear
        """
        self.logger.debug("Grok: Waiting for video generation...")

        start = asyncio.get_event_loop().time()
        check_interval = 5  # seconds

        while asyncio.get_event_loop().time() - start < timeout:
            try:
                # Check for completed video element
                video_el = page.locator('video[src*="assets.grok.com"]')
                if await video_el.count() > 0:
                    src = await video_el.first.get_attribute("src")
                    if src and "generated_video" in src:
                        self.logger.info(f"Grok: Video ready: {src[:80]}...")
                        return src

                # Also check video source elements
                source_el = page.locator('video source[src*="assets.grok.com"]')
                if await source_el.count() > 0:
                    src = await source_el.first.get_attribute("src")
                    if src:
                        self.logger.info(f"Grok: Video ready (source): {src[:80]}...")
                        return src

                # Check progress
                try:
                    progress_text = page.get_by_text("Gerando")
                    if await progress_text.is_visible(timeout=1000):
                        text = await progress_text.inner_text()
                        elapsed = int(asyncio.get_event_loop().time() - start)
                        self.logger.debug(f"Grok: {text} ({elapsed}s)")
                except (PlaywrightTimeout, Exception):
                    pass

                # Check for error
                try:
                    error_el = page.locator('[class*="error"], [class*="fail"]')
                    if await error_el.count() > 0:
                        error_text = await error_el.first.inner_text()
                        if error_text:
                            raise RuntimeError(f"Grok generation error: {error_text[:100]}")
                except (PlaywrightTimeout, Exception):
                    pass

            except RuntimeError:
                raise
            except Exception:
                pass

            await page.wait_for_timeout(check_interval * 1000)

        self.logger.warning("Grok: Video generation timed out")
        return None

    @retry_async(max_attempts=3)
    async def _download_video(self, cdn_url: str, idx: int) -> str:
        """Download a generated video from Grok CDN."""
        output_path = tempfile.mktemp(suffix=f"_broll_{idx:02d}.mp4")

        # Remove cache parameter if present
        clean_url = cdn_url.split("?")[0]

        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(clean_url)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)

        size_kb = os.path.getsize(output_path) / 1024
        self.logger.debug(f"Grok: Downloaded B-Roll {idx}: {size_kb:.0f}KB")
        return output_path

    async def generate_single(
        self,
        prompt: str,
        account_id: str,
        cookies: list[dict],
        proxy: dict | None = None,
        timeout: float = 300,
    ) -> str | None:
        """Convenience method for generating a single video."""
        results = await self.batch_generate(
            prompts=[prompt],
            account_id=account_id,
            cookies=cookies,
            proxy=proxy,
            batch_size=1,
            max_retries=2,
            timeout_per_video=timeout,
        )
        return results.get(0)


# Singleton
grok_automation = GrokAutomation()
