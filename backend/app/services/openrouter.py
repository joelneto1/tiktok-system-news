import json

import httpx

from app.config import settings
from app.utils.logger import logger
from app.utils.retry import retry_async


class OpenRouterClient:
    """Client for OpenRouter API (LLM text generation)."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://system-news-tiktok.local",
            "X-Title": "System News TikTok",
            "Content-Type": "application/json",
        }

    @retry_async(max_attempts=3, backoff_start=2.0, exceptions=(httpx.HTTPStatusError,))
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat completion request and return the response text.

        Retries automatically on 5xx and 429 (rate-limit) errors.
        """
        chosen_model = model or self.model
        payload = {
            "model": chosen_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(
            "OpenRouter request  | model={model} | user_msg={n} chars",
            model=chosen_model,
            n=len(user_message),
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self._headers(),
                json=payload,
            )

            # Retry only on 5xx or 429; let other errors propagate immediately
            if resp.status_code == 429 or resp.status_code >= 500:
                resp.raise_for_status()

            resp.raise_for_status()

            data = resp.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected OpenRouter response structure: {data}", data=data)
            raise ValueError(f"Could not parse OpenRouter response: {exc}") from exc

        logger.info(
            "OpenRouter response | model={model} | length={n} chars",
            model=chosen_model,
            n=len(content),
        )
        return content

    async def generate_script(
        self,
        topic: str,
        language: str = "pt-BR",
        system_prompt: str | None = None,
    ) -> str:
        """Generate a news script for the given topic.

        If no *system_prompt* is provided a default screenwriter prompt is used.
        Returns the raw script text.
        """
        default_prompt = (
            f"You are a screenwriter specialized in viral news videos "
            f"for TikTok and YouTube Shorts.\n"
            f"Generate a narration script for a vertical video (9:16) about the "
            f"given topic.\n\n"
            f"CRITICAL: The ENTIRE script MUST be written in {language}. "
            f"Every single word must be in {language}. Do NOT mix languages.\n\n"
            f"Rules:\n"
            f"- Language: {language} (mandatory, all output in this language)\n"
            f"- Narration duration: 45-90 seconds when read aloud\n"
            f"- Start with a STRONG HOOK in the first 3 seconds "
            f"(shocking question, surprising statement, urgent alert)\n"
            f"- Use SHORT and DIRECT sentences (max 15 words per sentence)\n"
            f"- Tone: urgent, journalistic, like breaking news\n"
            f"- No emojis or special formatting\n"
            f"- Only narration text, no scene directions or cues\n"
            f"- End with a strong call-to-action (CTA)\n\n"
            f"Return ONLY the script text, no titles or explanations."
        )

        prompt = system_prompt or default_prompt
        return await self.generate(prompt, f"Topic: {topic}")

    async def generate_scene_directions(
        self,
        script: str,
        timestamps: list[dict],
        system_prompt: str | None = None,
    ) -> dict:
        """Generate scene directions with B-Roll prompts and SFX timestamps.

        Returns a structured dict with ``scenes``, ``broll_prompts``, and
        ``sfx_cues`` parsed from the LLM JSON output.
        """
        default_prompt = (
            "You are a scene director for viral news videos.\n"
            "Receive the script with timestamps and define:\n"
            "1. Semantic blocks for B-Rolls (each block = 6 seconds of video)\n"
            "2. Text-to-video prompts for each B-Roll "
            "(in English, descriptive, cinematic)\n"
            "3. Exact moments for sound effects (SFX) at transitions\n\n"
            "Return a valid JSON with this structure:\n"
            "{\n"
            '  "scenes": [\n'
            "    {\n"
            '      "start_time": 0.0,\n'
            '      "end_time": 6.0,\n'
            '      "description": "semantic description of the scene",\n'
            '      "broll_prompt": "cinematic prompt in English for '
            'text-to-video generation",\n'
            '      "sfx": "whoosh"\n'
            "    }\n"
            "  ],\n"
            '  "urgent_keywords": ["keyword1", "keyword2"]\n'
            "}\n\n"
            "Rules:\n"
            "- Each scene must be exactly 6 seconds long\n"
            "- B-Roll prompts MUST be in ENGLISH, cinematic, detailed "
            '(e.g. "Aerial drone shot of a busy hospital emergency room, '
            'dramatic lighting, 4K")\n'
            '- SFX options: "whoosh", "impact", "ding", "tension_rise", '
            '"news_flash", null\n'
            "- Generate 2-5 urgent_keywords relevant to the topic"
        )

        prompt = system_prompt or default_prompt
        user_msg = f"Script:\n{script}\n\nTimestamps:\n{timestamps}"

        response = await self.generate(prompt, user_msg, temperature=0.3, max_tokens=8192)

        # Strip markdown code fences if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            # Remove first line (```json or ```)
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(
                "Failed to parse scene directions JSON: {err}\nRaw: {raw}",
                err=exc,
                raw=cleaned[:500],
            )
            raise ValueError(f"LLM returned invalid JSON for scene directions: {exc}") from exc


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
openrouter_client = OpenRouterClient()
