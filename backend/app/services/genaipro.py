from __future__ import annotations

import asyncio
import json
import time

import httpx

from app.config import settings
from app.utils.logger import logger
from app.utils.retry import retry_async


class GenAIProClient:
    """Client for GenAIPro Labs API (TTS + Subtitles)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GENAIPRO_API_KEY
        self.base_url = settings.GENAIPRO_BASE_URL  # https://genaipro.vn/api

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Voices
    # ------------------------------------------------------------------

    @retry_async(max_attempts=3, backoff_start=2.0, exceptions=(httpx.HTTPStatusError,))
    async def list_voices(
        self,
        language: str | None = None,
        category: str | None = None,
        page: int = 0,
        page_size: int = 30,
    ) -> list[dict]:
        """List available TTS voices."""
        params: dict = {"page": page, "page_size": page_size}
        if language:
            params["language"] = language
        if category:
            params["category"] = category

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/v1/labs/voices",
                headers=self._headers(),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Credits
    # ------------------------------------------------------------------

    @retry_async(max_attempts=3, backoff_start=2.0, exceptions=(httpx.HTTPStatusError,))
    async def get_credits(self) -> list[dict]:
        """Get TTS credit balance."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/v1/labs/credits",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    @retry_async(max_attempts=3, backoff_start=2.0, exceptions=(httpx.HTTPStatusError,))
    async def create_tts_task(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        speed: float = 1.0,
        stability: float = 0.75,
        similarity: float = 0.5,
        style: float = 0,
        use_speaker_boost: bool = True,
        callback_url: str | None = None,
    ) -> str:
        """Create a TTS task.  Returns ``task_id``."""
        body: dict = {
            "input": text,
            "voice_id": voice_id,
            "model_id": model_id,
            "speed": speed,
            "stability": stability,
            "similarity": similarity,
            "style": style,
            "use_speaker_boost": use_speaker_boost,
        }
        if callback_url:
            body["call_back_url"] = callback_url

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/labs/task",
                headers=self._headers(),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        task_id: str = data.get("task_id") or data.get("id", "")
        logger.info("TTS task created: {task_id}", task_id=task_id)
        return task_id

    @retry_async(max_attempts=3, backoff_start=2.0, exceptions=(httpx.HTTPStatusError,))
    async def get_task(self, task_id: str) -> dict:
        """Get TTS task status and result."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/v1/labs/task/{task_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Polling / WebSocket wait
    # ------------------------------------------------------------------

    async def poll_task(
        self,
        task_id: str,
        interval: float = 5.0,
        timeout: float = 300.0,
        on_progress: callable | None = None,
    ) -> dict:
        """Poll TTS task until completion or timeout.

        Returns the completed task payload.
        Raises ``TimeoutError`` if the task does not finish within *timeout*.
        Raises ``RuntimeError`` if the task reports failure.
        """
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            task = await self.get_task(task_id)
            status = task.get("status", "")

            if status == "completed":
                logger.success(
                    "TTS task {task_id} completed: {url}",
                    task_id=task_id,
                    url=str(task.get("result", ""))[:80],
                )
                return task

            if status == "failed":
                raise RuntimeError(f"TTS task {task_id} failed: {task}")

            if on_progress:
                on_progress(task)

            logger.debug("TTS task {task_id} status: {status}", task_id=task_id, status=status)
            await asyncio.sleep(interval)

        raise TimeoutError(f"TTS task {task_id} timed out after {timeout}s")

    async def wait_for_completion_ws(
        self,
        task_id: str,
        timeout: float = 300.0,
        on_progress: callable | None = None,
    ) -> dict:
        """Wait for TTS task via WebSocket (more efficient than polling).

        Falls back to :meth:`poll_task` if the WebSocket connection fails.
        """
        try:
            import websockets
        except ImportError:
            logger.warning("websockets package not installed, falling back to polling")
            return await self.poll_task(task_id, timeout=timeout, on_progress=on_progress)

        ws_url = f"wss://genaipro.vn/ws?token={self.api_key}"

        try:
            async with asyncio.timeout(timeout):
                async with websockets.connect(ws_url) as ws:
                    async for message in ws:
                        data = json.loads(message)
                        if data.get("type") == "labs_status_updated":
                            payload = data.get("payload", {})
                            if payload.get("task_id") == task_id:
                                pct = payload.get("process_percentage", 0)
                                logger.debug(
                                    "TTS task {task_id}: {pct}%",
                                    task_id=task_id,
                                    pct=pct,
                                )
                                if on_progress:
                                    on_progress(pct)
                                if pct >= 100:
                                    return await self.get_task(task_id)
        except Exception as exc:
            logger.warning(
                "WebSocket failed, falling back to polling: {err}",
                err=exc,
            )
            return await self.poll_task(task_id, timeout=timeout, on_progress=on_progress)

    # ------------------------------------------------------------------
    # Subtitles
    # ------------------------------------------------------------------

    @retry_async(max_attempts=3, backoff_start=2.0, exceptions=(httpx.HTTPStatusError,))
    async def get_subtitles(
        self,
        task_id: str,
        max_chars_per_line: int = 42,
        max_lines_per_cue: int = 2,
        max_seconds_per_cue: float = 7.0,
    ) -> str:
        """Export subtitles (SRT) from a completed TTS task."""
        body = {
            "max_characters_per_line": max_chars_per_line,
            "max_lines_per_cue": max_lines_per_cue,
            "max_seconds_per_cue": max_seconds_per_cue,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/labs/task/subtitle/{task_id}",
                headers=self._headers(),
                json=body,
            )
            resp.raise_for_status()
            return resp.text

    # ------------------------------------------------------------------
    # Audio download
    # ------------------------------------------------------------------

    @retry_async(max_attempts=3, backoff_start=2.0, exceptions=(httpx.HTTPStatusError,))
    async def download_audio(self, audio_url: str) -> bytes:
        """Download the generated audio file from the CDN URL."""
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            resp = await client.get(audio_url)
            resp.raise_for_status()
            logger.info(
                "Downloaded TTS audio: {n} bytes",
                n=len(resp.content),
            )
            return resp.content


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
genaipro_client = GenAIProClient()
