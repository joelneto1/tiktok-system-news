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
        timeout: float = 720,
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
            await self._wait_for_completion(creation_page, timeout, on_progress, project_name=project_name)
            print("[DreamFace] 7/8 Processamento concluido!", flush=True)

            # Step 8: Download result from the creation tab (same tab that "Gerar" opened)
            print("[DreamFace] 8/8 Baixando video resultado...", flush=True)
            if on_progress:
                on_progress("Downloading result...")
            # Reload the creation page to ensure video is loaded
            await creation_page.reload(wait_until="networkidle")
            await creation_page.wait_for_timeout(5000)
            print(f"[DreamFace] 8/8 Pagina recarregada: {creation_page.url}", flush=True)
            output_path = await self._download_result(creation_page, project_name=project_name)
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

        # Count thumbnails BEFORE upload
        thumbs_before = page.locator("._imgStyle_m7pad_15")
        count_before = await thumbs_before.count()
        print(f"[DreamFace] Thumbnails ANTES do upload: {count_before}", flush=True)

        # Upload file — make hidden input visible and click it directly
        uploaded = False

        # Approach 1: Make input visible, click it, intercept filechooser
        print("[DreamFace] Tornando input[type=file] visivel...", flush=True)
        try:
            await page.evaluate('''() => {
                const input = document.querySelector('input[type="file"]');
                if (input) {
                    input.style.display = 'block';
                    input.style.opacity = '1';
                    input.style.position = 'fixed';
                    input.style.top = '50px';
                    input.style.left = '50px';
                    input.style.width = '200px';
                    input.style.height = '50px';
                    input.style.zIndex = '99999';
                    return 'INPUT_VISIBLE';
                }
                return 'NO_INPUT';
            }''')

            print("[DreamFace] Clicando no input visivel + filechooser...", flush=True)
            async with page.expect_file_chooser(timeout=10000) as fc_info:
                await page.locator('input[type="file"]').click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(video_path)
            print(f"[DreamFace] Arquivo enviado via input visivel: {video_path}", flush=True)
            uploaded = True
        except Exception as e:
            print(f"[DreamFace] Input visivel falhou: {e}", flush=True)

        # Approach 2: Fallback - _btnContent click + filechooser
        if not uploaded:
            print("[DreamFace] Tentando via _btnContent + filechooser...", flush=True)
            try:
                btn = page.locator('[class*="_btnContent"]')
                if await btn.count() > 0:
                    async with page.expect_file_chooser(timeout=10000) as fc_info:
                        await btn.first.click()
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(video_path)
                    print("[DreamFace] Arquivo enviado via _btnContent!", flush=True)
                    uploaded = True
            except Exception as e:
                print(f"[DreamFace] _btnContent falhou: {e}", flush=True)

        if not uploaded:
            print("[DreamFace] Tentando via filechooser...", flush=True)
            try:
                # Find and click upload button
                upload_btn = page.locator('[class*="upload"], [class*="Upload"], button:has-text("Upload"), button:has-text("Carregar")')
                if await upload_btn.count() > 0:
                    async with page.expect_file_chooser(timeout=5000) as fc_info:
                        await upload_btn.first.click()
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(video_path)
                    print("[DreamFace] Arquivo enviado via filechooser", flush=True)
                    uploaded = True
            except Exception as e:
                print(f"[DreamFace] Filechooser falhou: {e}", flush=True)

        if not uploaded:
            print("[DreamFace] AVISO: Nenhum metodo de upload funcionou!", flush=True)

        # Wait for upload to process (DreamFace needs ~5-8s to show new thumbnail)
        print("[DreamFace] Aguardando thumbnail aparecer (10s)...", flush=True)
        await page.wait_for_timeout(10000)

        # Count thumbnails AFTER upload
        thumbs_after = page.locator("._imgStyle_m7pad_15")
        count_after = await thumbs_after.count()
        print(f"[DreamFace] Thumbnails DEPOIS do upload: {count_after}", flush=True)

        if count_after > count_before:
            print(f"[DreamFace] NOVO thumbnail detectado! Upload funcionou.", flush=True)
        else:
            print(f"[DreamFace] AVISO: Nenhum novo thumbnail! Upload pode ter falhado.", flush=True)

        # MUST click on the new thumbnail to confirm selection
        try:
            thumbs = page.locator("._imgStyle_m7pad_15")
            count = await thumbs.count()
            print(f"[DreamFace] Total thumbnails: {count}", flush=True)

            if count > 0:
                # Clicar no PRIMEIRO thumbnail (DreamFace mostra recentes primeiro)
                await thumbs.nth(0).click()
                await page.wait_for_timeout(2000)

                # Verificar se ficou selecionado (class _selected_m7pad_23)
                is_selected = await page.evaluate('''() => {
                    const selected = document.querySelector('._selected_m7pad_23');
                    return selected !== null;
                }''')

                if is_selected:
                    print("[DreamFace] Thumbnail 1 selecionado e CONFIRMADO (_selected_m7pad_23)!", flush=True)
                else:
                    print("[DreamFace] AVISO: Thumbnail clicado mas nao confirmou selecao", flush=True)
                    # Tentar clicar de novo
                    await thumbs.nth(0).click()
                    await page.wait_for_timeout(2000)
                    is_selected2 = await page.evaluate('''() => {
                        return document.querySelector('._selected_m7pad_23') !== null;
                    }''')
                    print(f"[DreamFace] Segunda tentativa: selecionado={is_selected2}", flush=True)

                # Screenshot pra debug
                await page.screenshot(path="/tmp/dreamface_thumb_selected.png")
                print("[DreamFace] Screenshot: /tmp/dreamface_thumb_selected.png", flush=True)
            else:
                print("[DreamFace] ERRO: Nenhum thumbnail encontrado!", flush=True)
                raise RuntimeError("DreamFace: Nenhum thumbnail disponivel")
        except Exception as e:
            print(f"[DreamFace] Erro ao selecionar thumbnail: {e}", flush=True)

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

        # Wait for audio to process — Gerar button stays disabled until ready
        print("[DreamFace] Aguardando audio processar (botao Gerar fica disabled ate carregar)...", flush=True)
        for i in range(12):
            await page.wait_for_timeout(5000)
            is_disabled = await page.evaluate('''() => {
                const btns = document.querySelectorAll('button');
                for (const b of btns) {
                    if (b.innerText.includes('Gerar')) return b.disabled;
                }
                return true;
            }''')
            if not is_disabled:
                print(f"[DreamFace] Botao Gerar HABILITADO! ({(i+1)*5}s)", flush=True)
                break
            print(f"[DreamFace] Botao Gerar ainda disabled ({(i+1)*5}s)...", flush=True)
        else:
            print("[DreamFace] AVISO: Botao Gerar ainda disabled apos 60s", flush=True)

    async def _click_generate(self, page: Page) -> Page:
        """Click Generate button — opens /creation page in new tab."""
        print("[DreamFace] Clicando em Gerar...", flush=True)

        # Screenshot before clicking to debug
        await page.screenshot(path="/tmp/dreamface_before_gerar.png")

        # Check if button is enabled
        btn_info = await page.evaluate('''() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.innerText.includes('Gerar') || b.innerText.includes('Generate')) {
                    return {text: b.innerText.substring(0,20), disabled: b.disabled, visible: b.offsetParent !== null};
                }
            }
            return null;
        }''')
        print(f"[DreamFace] Botao Gerar: {btn_info}", flush=True)

        # Try clicking with expect_page (longer timeout)
        try:
            async with page.context.expect_page(timeout=60000) as new_page_info:
                # Use JavaScript click to bypass any overlay
                await page.evaluate('''() => {
                    const btns = document.querySelectorAll('button');
                    for (const b of btns) {
                        if (b.innerText.includes('Gerar') || b.innerText.includes('Generate')) {
                            b.click();
                            return true;
                        }
                    }
                    return false;
                }''')
                print("[DreamFace] Gerar clicado via JS, esperando nova pagina (60s)...", flush=True)

            creation_page = await new_page_info.value
            await creation_page.wait_for_load_state("networkidle", timeout=30000)
            print(f"[DreamFace] Nova pagina aberta: {creation_page.url}", flush=True)
            return creation_page
        except Exception as e:
            print(f"[DreamFace] Expect_page falhou: {e}", flush=True)
            await page.screenshot(path="/tmp/dreamface_after_gerar.png")
            print(f"[DreamFace] URL apos clique: {page.url}", flush=True)

            # Check all pages in context
            pages = page.context.pages
            print(f"[DreamFace] Total de abas abertas: {len(pages)}", flush=True)
            for i, p in enumerate(pages):
                print(f"[DreamFace]   Aba {i}: {p.url}", flush=True)

            # If there's a second page (creation), use it
            if len(pages) > 1:
                for p in pages:
                    if "creation" in p.url:
                        print(f"[DreamFace] Encontrou aba /creation: {p.url}", flush=True)
                        return p
                # Use last page
                return pages[-1]

            # Return same page — _wait_for_completion navigates to /creation
            print("[DreamFace] Usando mesma pagina (vai navegar pra /creation)", flush=True)
            return page

    async def _wait_for_completion(
        self,
        page: Page,
        timeout: float = 720,
        on_progress=None,
        project_name: str = "",
    ):
        """Wait for video generation to complete on the creation page.

        Finds our specific project by name (news_{job_id[:8]}.mp3) and
        waits for it to have a video/thumbnail result.
        """
        # Extract audio filename from project name for searching on /creation
        # Project name: "News 6687e936: topic..." -> audio: "news_6687e936"
        audio_name = ""
        if project_name:
            parts = project_name.split(":")
            if parts:
                audio_name = parts[0].strip().replace("News ", "news_")  # "news_6687e936"
        print(f"[DreamFace] Aguardando video ficar pronto (timeout: {timeout}s, busca: {audio_name})...", flush=True)

        start = asyncio.get_event_loop().time()
        check_interval = 30  # Check /creation every 30 seconds
        min_wait = 120  # Minimum 2 minutes before checking /creation

        while asyncio.get_event_loop().time() - start < timeout:
            elapsed = int(asyncio.get_event_loop().time() - start)

            if elapsed < min_wait:
                print(f"[DreamFace] Aguardando... ({elapsed}s, checagem em {min_wait - elapsed}s)", flush=True)
                if on_progress:
                    on_progress(f"Processing... ({elapsed}s)")
                await page.wait_for_timeout(10000)
                continue

            # Navigate to /creation and check if our video exists
            try:
                print(f"[DreamFace] Verificando /creation... ({elapsed}s)", flush=True)
                await page.goto("https://www.dreamfaceapp.com/creation", wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(5000)

                # Search for our audio name in the page
                found = await page.evaluate('''(audioName) => {
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                    while (walker.nextNode()) {
                        if (walker.currentNode.textContent.includes(audioName)) {
                            // Check if the parent card has an img (= video ready, not generating)
                            let el = walker.currentNode.parentElement;
                            for (let i = 0; i < 5; i++) {
                                if (el.parentElement) el = el.parentElement;
                                const img = el.querySelector('img');
                                if (img && img.src) {
                                    // Check if this card shows "Generating" text
                                    const text = el.innerText || '';
                                    if (text.includes('Gerando') || text.includes('Generating')) {
                                        return {status: 'generating'};
                                    }
                                    return {status: 'ready', img: img.src.substring(0, 80)};
                                }
                            }
                            return {status: 'found_no_img'};
                        }
                    }
                    return {status: 'not_found'};
                }''', audio_name)

                status = found.get("status", "not_found")
                print(f"[DreamFace] Status do video: {status} ({elapsed}s)", flush=True)

                if status == "ready":
                    print(f"[DreamFace] Video PRONTO na /creation! ({elapsed}s)", flush=True)
                    return
                elif status == "generating":
                    print(f"[DreamFace] Ainda gerando... ({elapsed}s)", flush=True)
                elif status == "not_found":
                    print(f"[DreamFace] Video nao encontrado na /creation, scrollando... ({elapsed}s)", flush=True)
                    for _ in range(3):
                        await page.evaluate('window.scrollBy(0, 500)')
                        await page.wait_for_timeout(1000)

            except Exception as e:
                print(f"[DreamFace] Erro ao verificar /creation: {e}", flush=True)

            await page.wait_for_timeout(check_interval * 1000)

        raise TimeoutError(
            f"DreamFace: Video '{audio_name}' nao ficou pronto em {timeout}s"
        )

    async def _download_result(self, page: Page, project_name: str = "") -> str:
        """Download the result video from DreamFace /creation page.
        Navigates to /creation, finds our project by audio name, clicks img to open modal,
        gets video.src CDN URL, downloads via httpx.
        """
        # The audio name is news_{job_id[:8]}.mp3
        # Extract job_id from project_name: "News 6687e936: topic..."
        search_term = ""
        if project_name:
            parts = project_name.split(":")
            if parts:
                # "News 6687e936" -> search for "news_6687e936"
                search_term = parts[0].strip().replace("News ", "news_")

        print(f"[DreamFace] Tentando baixar resultado (projeto: {search_term})...", flush=True)

        output_path = tempfile.mktemp(suffix=".mp4")

        # Step 1: Navigate to /creation page
        print("[DreamFace] Navegando para /creation...", flush=True)
        await page.goto("https://www.dreamfaceapp.com/creation", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)

        img_count = await page.evaluate('() => document.querySelectorAll("img").length')
        print(f"[DreamFace] Pagina /creation carregada: {img_count} imagens", flush=True)

        # Step 2: Find our card by name and click the IMG to open modal
        for attempt in range(5):
            clicked = await page.evaluate('''(searchTerm) => {
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                while (walker.nextNode()) {
                    if (walker.currentNode.textContent.includes(searchTerm)) {
                        let el = walker.currentNode.parentElement;
                        for (let i = 0; i < 5; i++) {
                            if (el.parentElement) el = el.parentElement;
                            const img = el.querySelector('img');
                            if (img) { img.click(); return 'clicked_img'; }
                        }
                    }
                }
                return 'not_found';
            }''', search_term)

            print(f"[DreamFace] Tentativa {attempt+1}/5: {clicked}", flush=True)

            if clicked == 'clicked_img':
                # Wait for modal to load
                await page.wait_for_timeout(8000)

                # Get video.src from modal
                video_url = await page.evaluate('''() => {
                    const video = document.querySelector('video');
                    if (video && video.src) return video.src;
                    if (video && video.currentSrc) return video.currentSrc;
                    return null;
                }''')

                if video_url:
                    print(f"[DreamFace] CDN URL encontrada: {video_url[:80]}...", flush=True)
                    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                        resp = await client.get(video_url)
                        resp.raise_for_status()
                        with open(output_path, "wb") as f:
                            f.write(resp.content)
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    if size_mb > 0.1:
                        print(f"[DreamFace] Video baixado: {size_mb:.1f}MB", flush=True)
                        return output_path
                    else:
                        print(f"[DreamFace] Arquivo muito pequeno ({size_mb:.1f}MB), tentando novamente...", flush=True)
                else:
                    print(f"[DreamFace] Modal aberto mas video.src nao encontrado, tentando novamente...", flush=True)
                    # Close modal and try again
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(2000)
            else:
                print(f"[DreamFace] Card '{search_term}' nao encontrado, scrollando...", flush=True)
                await page.evaluate('window.scrollBy(0, 500)')
                await page.wait_for_timeout(3000)

        raise RuntimeError(f"DreamFace: Nao foi possivel baixar o video '{search_term}' apos 5 tentativas")
        return output_path


# Singleton
dreamface_automation = DreamFaceAutomation()
