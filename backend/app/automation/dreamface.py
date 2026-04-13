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
            print("[DreamFace] Iniciando geracao do avatar...", flush=True)

            # Step 1: Navigate
            print("[DreamFace] 1/8 Navegando para DreamFace...", flush=True)
            await page.goto("https://www.dreamfaceapp.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(1000)

            print("[DreamFace] 1/8 Injetando localStorage (autenticacao)...", flush=True)
            await self._inject_local_storage(page, cookies)

            await page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            print(f"[DreamFace] 1/8 Pagina carregada: {page.url}", flush=True)

            # Step 2: Accept cookies banner
            print("[DreamFace] 2/8 Verificando banner de cookies...", flush=True)
            await self._accept_cookies(page)

            # Step 3: Check login
            print("[DreamFace] 3/8 Verificando login...", flush=True)
            await self._ensure_logged_in(page)

            # Step 4: Upload reference video
            print("[DreamFace] 4/8 Fazendo upload do video de referencia...", flush=True)
            if on_progress:
                on_progress("Uploading reference video...")
            await self._upload_reference_video(page, reference_video_path)
            print("[DreamFace] 4/8 Video de referencia enviado!", flush=True)

            # Step 5: Upload TTS audio
            print("[DreamFace] 5/8 Fazendo upload do audio TTS...", flush=True)
            if on_progress:
                on_progress("Uploading TTS audio...")
            await self._upload_audio(page, tts_audio_path)
            print("[DreamFace] 5/8 Audio TTS enviado!", flush=True)

            # Step 6: Click Generate
            print("[DreamFace] 6/8 Clicando em Gerar...", flush=True)
            if on_progress:
                on_progress("Starting generation...")
            creation_page = await self._click_generate(page)
            print("[DreamFace] 6/8 Geracao iniciada!", flush=True)

            # Step 7: Wait for completion
            print("[DreamFace] 7/8 Aguardando processamento (2-5 min)...", flush=True)
            if on_progress:
                on_progress("Waiting for DreamFace to process (2-5 min)...")
            await self._wait_for_completion(creation_page, timeout, on_progress)
            print("[DreamFace] 7/8 Processamento concluido!", flush=True)

            # Step 8: Download result
            print("[DreamFace] 8/8 Baixando video resultado...", flush=True)
            if on_progress:
                on_progress("Downloading result...")
            output_path = await self._download_result(creation_page)
            print(f"[DreamFace] 8/8 Video baixado: {output_path}", flush=True)
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

        # Upload file via hidden file input (bypasses file picker)
        file_inputs = await page.query_selector_all('input[type="file"]')
        if file_inputs:
            await file_inputs[0].set_input_files(video_path)
            self.logger.info("DreamFace: Reference video file set via input[type=file]")
        else:
            # Fallback: try setting on body
            await page.locator("body").set_input_files(video_path)
            self.logger.info("DreamFace: Reference video file set via body")
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

        # Upload file via hidden file input (bypasses file picker)
        file_inputs = await page.query_selector_all('input[type="file"]')
        if file_inputs:
            await file_inputs[-1].set_input_files(audio_path)
            self.logger.info("DreamFace: Audio file set via input[type=file]")
        else:
            await page.locator("body").set_input_files(audio_path)
            self.logger.info("DreamFace: Audio file set via body")
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
        """Download the result video from DreamFace creation page."""
        print("[DreamFace] Tentando baixar resultado...", flush=True)

        output_path = tempfile.mktemp(suffix=".mp4")

        # Strategy 1: Try to find video URL directly on the page
        for attempt in range(3):
            video_url = await page.evaluate('''() => {
                const videos = document.querySelectorAll('video');
                for (const v of videos) {
                    if (v.src && v.src.includes('http')) return v.src;
                }
                const sources = document.querySelectorAll('video source');
                for (const s of sources) {
                    if (s.src && s.src.includes('http')) return s.src;
                }
                const links = document.querySelectorAll('a[href*=".mp4"]');
                for (const l of links) {
                    if (l.href) return l.href;
                }
                return null;
            }''')

            if video_url:
                print(f"[DreamFace] URL do video encontrada: {video_url[:80]}...", flush=True)
                async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                    resp = await client.get(video_url)
                    resp.raise_for_status()
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                if size_mb > 0.1:
                    return output_path

            print(f"[DreamFace] Tentativa {attempt+1}/3: video nao encontrado, clicando no card...", flush=True)

            # Click on creation card to open modal
            await page.evaluate('''() => {
                const cards = document.querySelectorAll('[class*="creationList"] > *');
                if (cards.length > 0) { cards[0].querySelector('img, [class*="operate"]')?.click() || cards[0].click(); }
            }''')
            await page.wait_for_timeout(5000)

        # Strategy 2: Try download button
        print("[DreamFace] Tentando botao de download...", flush=True)
        for btn_name in ["Baixar", "Download", "Descargar"]:
            try:
                btn = page.get_by_role("button", name=btn_name)
                if await btn.count() > 0:
                    async with page.expect_download(timeout=30000) as download_info:
                        await btn.click()
                    download = await download_info.value
                    await download.save_as(output_path)
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    if size_mb > 0.1:
                        print(f"[DreamFace] Baixado via botao {btn_name}: {size_mb:.1f}MB", flush=True)
                        return output_path
            except Exception:
                continue

        # Strategy 3: Try any download link
        print("[DreamFace] Tentando links de download na pagina...", flush=True)
        download_url = await page.evaluate('''() => {
            const links = document.querySelectorAll('a[download], a[href*="download"], a[href*=".mp4"]');
            for (const l of links) { if (l.href) return l.href; }
            return null;
        }''')
        if download_url:
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                resp = await client.get(download_url)
                resp.raise_for_status()
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return output_path

        raise RuntimeError("DreamFace: Nao foi possivel baixar o video resultado")

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        self.logger.success(f"DreamFace: Downloaded {size_mb:.1f}MB to {output_path}")
        return output_path


# Singleton
dreamface_automation = DreamFaceAutomation()
