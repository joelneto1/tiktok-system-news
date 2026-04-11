"""DreamFace avatar generation automation via Playwright.

Mapped from Playwright Codegen recording of the actual DreamFace flow:
1. Navigate to /pt/avatar
2. Accept cookies (if shown)
3. Login check (via saved cookies)
4. Click "Fotos/Videos" to open upload
5. Upload reference video via set_input_files
6. Select the uploaded video thumbnail
7. Click "Audio" tab
8. Click "Carregar Audio ou Video" → "Upload"
9. Upload TTS audio via set_input_files
10. Click "Gerar" (Generate) — opens new tab /pt/creation
11. Monitor creation page — wait for "Gerando..." to disappear
12. Click on completed card (._operate_1jvc3_1)
13. Click "Baixar" (Download) via expect_download
"""

import asyncio
import os
import re
import tempfile

import httpx
from playwright.async_api import Page, BrowserContext, TimeoutError as PlaywrightTimeout

from app.automation.browser_pool import browser_pool
from app.utils.logger import logger
from app.utils.retry import retry_async


class DreamFaceAutomation:
    """Automates DreamFace avatar lip-sync generation via Playwright."""

    BASE_URL = "https://www.dreamfaceapp.com/pt/avatar"
    CREATION_URL = "https://www.dreamfaceapp.com/pt/creation"

    def __init__(self):
        self.logger = logger

    async def process_avatar(
        self,
        account_id: str,
        cookies: list[dict],
        proxy: dict | None,
        reference_video_path: str,
        tts_audio_path: str,
        project_name: str = "News Video",
        timeout: float = 600,
        on_progress=None,
    ) -> str:
        """Full DreamFace automation flow.

        Args:
            account_id: Account ID for browser context
            cookies: Cookies for authentication
            proxy: Optional proxy config
            reference_video_path: Local path to the green-screen reference video
            tts_audio_path: Local path to the TTS audio file
            project_name: Name for the project
            timeout: Maximum wait time in seconds
            on_progress: Optional callback for progress updates

        Returns:
            Local path to the downloaded result video
        """
        pw, browser, ctx, page = await browser_pool.get_page(
            account_id, cookies=cookies, proxy=proxy
        )

        try:
            self.logger.info("DreamFace: Starting avatar generation")

            # Step 1: Navigate to DreamFace domain first (needed to set localStorage)
            if on_progress:
                on_progress("Navigating to DreamFace...")

            # Go to a simple page first to set localStorage for auth
            await page.goto("https://www.dreamfaceapp.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(1000)

            # Inject localStorage auth data from cookies (which contain localStorage JSON)
            await self._inject_local_storage(page, cookies)

            # Now navigate to avatar page with auth
            await page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # Step 2: Accept cookies banner (if shown)
            await self._accept_cookies(page)

            # Step 3: Check if logged in
            await self._ensure_logged_in(page)

            # Step 4: Upload reference video
            if on_progress:
                on_progress("Uploading reference video...")
            await self._upload_reference_video(page, reference_video_path)

            # Step 5: Upload TTS audio
            if on_progress:
                on_progress("Uploading TTS audio...")
            await self._upload_audio(page, tts_audio_path)

            # Step 6: Click Generate — opens new tab
            if on_progress:
                on_progress("Starting generation...")
            creation_page = await self._click_generate(page)

            # Step 7: Wait for completion on creation page
            if on_progress:
                on_progress("Waiting for DreamFace to process (2-5 min)...")
            await self._wait_for_completion(creation_page, timeout, on_progress)

            # Step 8: Download result
            if on_progress:
                on_progress("Downloading result...")
            output_path = await self._download_result(creation_page)

            self.logger.success(f"DreamFace: Avatar ready at {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"DreamFace automation failed: {e}")
            try:
                screenshot_path = tempfile.mktemp(suffix=".png")
                await page.screenshot(path=screenshot_path)
                self.logger.debug(f"Debug screenshot saved: {screenshot_path}")
            except Exception:
                pass
            raise
        finally:
            await browser_pool.release(pw, browser, ctx)

    async def _inject_local_storage(self, page: Page, cookies: list[dict]):
        """Inject localStorage auth data for DreamFace.

        The 'cookies' parameter contains localStorage key-value pairs
        as list of {name, value} dicts.
        """
        import json as _json
        count = 0
        try:
            for item in cookies:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    name = item["name"]
                    value = item["value"]
                    await page.evaluate(
                        f'localStorage.setItem({_json.dumps(name)}, {_json.dumps(value)})'
                    )
                    count += 1

            self.logger.info(f"DreamFace: Injected {count} localStorage items")
        except Exception as e:
            self.logger.warning(f"DreamFace: Failed to inject localStorage: {e}")

    async def _accept_cookies(self, page: Page):
        """Accept cookie banner if present."""
        try:
            accept_btn = page.get_by_role("button", name="Aceitar")
            if await accept_btn.is_visible(timeout=3000):
                await accept_btn.click()
                self.logger.debug("DreamFace: Cookie banner accepted")
                await page.wait_for_timeout(1000)
        except (PlaywrightTimeout, Exception):
            pass

    async def _ensure_logged_in(self, page: Page):
        """Check if logged in. If login button is visible, cookies expired."""
        try:
            login_btn = page.get_by_role("button", name="Entrar/Cadastro")
            if await login_btn.is_visible(timeout=3000):
                self.logger.warning("DreamFace: Not logged in — cookies expired")
                raise RuntimeError(
                    "DreamFace session expired. Update cookies in Connections page."
                )
        except PlaywrightTimeout:
            self.logger.info("DreamFace: Logged in via cookies")

    async def _upload_reference_video(self, page: Page, video_path: str):
        """Upload the reference video (green screen avatar).

        Flow: Close popups → Click "Fotos/Videos" → Dismiss tooltip → Upload file → Select thumbnail
        """
        self.logger.info(f"DreamFace: Uploading reference video: {video_path}")

        # Close any initial popup/modal
        try:
            close_btn = page.get_by_role("button").first
            if await close_btn.is_visible(timeout=2000):
                await close_btn.click()
                await page.wait_for_timeout(500)
        except (PlaywrightTimeout, Exception):
            pass

        # Click "Fotos/Videos" tab
        try:
            photos_tab = page.locator("div").filter(
                has_text=re.compile(r"^Fotos/Vídeos$")
            ).nth(2)
            await photos_tab.click()
            await page.wait_for_timeout(1000)
        except Exception:
            photos_tab = page.get_by_text("Fotos/Vídeos")
            await photos_tab.click()
            await page.wait_for_timeout(1000)

        # Dismiss "Entendi" tooltip if shown
        try:
            entendi_btn = page.get_by_text("Entendi")
            if await entendi_btn.is_visible(timeout=2000):
                await entendi_btn.click()
                await page.wait_for_timeout(500)
        except (PlaywrightTimeout, Exception):
            pass

        # Click "Fotos/Videos" again (sometimes needed after dismissing tooltip)
        try:
            photos_tab = page.locator("div").filter(
                has_text=re.compile(r"^Fotos/Vídeos$")
            ).nth(2)
            await photos_tab.click()
            await page.wait_for_timeout(1000)
        except Exception:
            pass

        # Upload file via hidden input (bypasses file picker)
        await page.locator("body").set_input_files(video_path)
        self.logger.info("DreamFace: Reference video file set")
        await page.wait_for_timeout(3000)

        # Select the uploaded video (first thumbnail with class _imgStyle_m7pad_15)
        try:
            first_thumb = page.locator("._imgStyle_m7pad_15").first
            await first_thumb.click()
            await page.wait_for_timeout(1000)
            self.logger.info("DreamFace: Reference video selected")
        except Exception as e:
            self.logger.warning(f"DreamFace: Could not select thumbnail: {e}")

    async def _upload_audio(self, page: Page, audio_path: str):
        """Upload the TTS audio file.

        Flow: Click "Audio" tab → Click "Carregar Audio ou Video" → Click "Upload" → Upload file
        """
        self.logger.info(f"DreamFace: Uploading TTS audio: {audio_path}")

        # Click "Audio" tab
        await page.get_by_text("Áudio", exact=True).click()
        await page.wait_for_timeout(1000)

        # Click "Carregar Audio ou Video" area
        try:
            upload_area = page.locator("div").filter(
                has_text=re.compile(r"^Carregar Áudio ou Vídeo$")
            ).nth(1)
            await upload_area.click()
            await page.wait_for_timeout(500)
        except Exception:
            pass

        # Click "Upload" button
        try:
            upload_btn = page.get_by_text("Upload")
            if await upload_btn.is_visible(timeout=2000):
                await upload_btn.click()
                await page.wait_for_timeout(500)
        except (PlaywrightTimeout, Exception):
            pass

        # Upload file via hidden input (bypasses file picker)
        await page.locator("body").set_input_files(audio_path)
        self.logger.info("DreamFace: Audio file set")
        await page.wait_for_timeout(3000)

    async def _click_generate(self, page: Page) -> Page:
        """Click the Generate button. Opens new tab with creation page.

        Returns the new Page (creation tab).
        """
        self.logger.info("DreamFace: Clicking Generate...")

        # expect_page() captures the new tab that opens
        async with page.context.expect_page() as new_page_info:
            await page.get_by_role("button", name="Gerar").click()

        creation_page = await new_page_info.value
        await creation_page.wait_for_load_state("networkidle")
        self.logger.info(f"DreamFace: Creation page opened: {creation_page.url}")
        return creation_page

    async def _wait_for_completion(
        self,
        page: Page,
        timeout: float = 600,
        on_progress=None,
    ):
        """Wait for video generation to complete on the creation page.

        Monitors for "Gerando..." text to disappear from the first card.
        When it disappears, the video is ready for download.
        """
        self.logger.info(f"DreamFace: Waiting for completion (timeout: {timeout}s)...")

        start = asyncio.get_event_loop().time()
        check_interval = 10  # seconds

        while asyncio.get_event_loop().time() - start < timeout:
            try:
                # Check if "Gerando..." is still visible on the page
                generating_text = page.get_by_text("Gerando...")
                is_generating = await generating_text.is_visible(timeout=3000)

                if not is_generating:
                    self.logger.success("DreamFace: Generation complete!")
                    await page.wait_for_timeout(2000)
                    return

                elapsed = int(asyncio.get_event_loop().time() - start)
                self.logger.debug(
                    f"DreamFace: Still generating... ({elapsed}s / {int(timeout)}s)"
                )
                if on_progress:
                    on_progress(f"Processing... ({elapsed}s)")

            except PlaywrightTimeout:
                # "Gerando..." text not found — generation may be complete
                self.logger.info("DreamFace: 'Gerando...' not found — likely complete")
                await page.wait_for_timeout(2000)
                return
            except Exception as e:
                self.logger.debug(f"DreamFace: Check error: {e}")

            await page.wait_for_timeout(check_interval * 1000)

            # Refresh page every 30s to get updated status
            elapsed = int(asyncio.get_event_loop().time() - start)
            if elapsed > 0 and elapsed % 30 == 0:
                try:
                    await page.reload(wait_until="networkidle")
                except Exception:
                    pass

        raise TimeoutError(
            f"DreamFace: Processing did not complete within {timeout}s"
        )

    async def _download_result(self, page: Page) -> str:
        """Click on the completed card and download the result video.

        Flow: Click first card (._operate_1jvc3_1) → Dialog opens → Click "Baixar" → Save download
        """
        self.logger.info("DreamFace: Downloading result...")

        # Click on the first card's operate button (most recent creation)
        try:
            first_card = page.locator("._operate_1jvc3_1").first
            await first_card.click()
            await page.wait_for_timeout(2000)
        except Exception:
            # Fallback: click on the first thumbnail image
            try:
                first_thumb = page.locator("img").first
                await first_thumb.click()
                await page.wait_for_timeout(2000)
            except Exception as e:
                raise RuntimeError(f"DreamFace: Could not click on result card: {e}")

        # Download via "Baixar" button with expect_download
        output_path = tempfile.mktemp(suffix=".mp4")

        try:
            async with page.expect_download(timeout=60000) as download_info:
                await page.get_by_role("button", name="Baixar").click()

            download = await download_info.value
            await download.save_as(output_path)
        except Exception as e:
            # Fallback: try to find download link in the dialog
            self.logger.warning(f"DreamFace: expect_download failed: {e}")
            try:
                download_link = page.locator("a[download], a[href*='.mp4']").first
                href = await download_link.get_attribute("href")
                if href:
                    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                        resp = await client.get(href)
                        resp.raise_for_status()
                        with open(output_path, "wb") as f:
                            f.write(resp.content)
                else:
                    raise RuntimeError("No download URL found")
            except Exception as e2:
                raise RuntimeError(f"DreamFace: Download failed: {e2}")

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        self.logger.success(f"DreamFace: Downloaded {size_mb:.1f}MB to {output_path}")
        return output_path


# Singleton
dreamface_automation = DreamFaceAutomation()
