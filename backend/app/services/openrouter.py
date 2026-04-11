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
            f"Voce e um roteirista especializado em videos virais de noticias "
            f"para TikTok e YouTube Shorts.\n"
            f"Gere um roteiro de narracao para um video vertical (9:16) sobre o "
            f"topico fornecido.\n\n"
            f"Regras:\n"
            f"- Idioma: {language}\n"
            f"- Duracao da narracao: 45-90 segundos quando lido em voz alta\n"
            f"- Comece com um HOOK forte nos primeiros 3 segundos "
            f"(pergunta chocante, afirmacao surpreendente, alerta urgente)\n"
            f"- Use frases CURTAS e DIRETAS (maximo 15 palavras por frase)\n"
            f"- Tom: urgente, jornalistico, como breaking news\n"
            f"- Nao use emojis ou formatacao especial\n"
            f"- Apenas o texto da narracao, sem indicacoes de cena ou direcoes\n"
            f"- Termine com uma chamada para acao (CTA) forte\n\n"
            f"Retorne APENAS o texto do roteiro, sem titulos ou explicacoes."
        )

        prompt = system_prompt or default_prompt
        return await self.generate(prompt, f"Topico: {topic}")

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
            "Voce e um diretor de cena para videos de noticias virais.\n"
            "Receba o roteiro com timestamps e defina:\n"
            "1. Blocos semanticos para B-Rolls (cada bloco = 6 segundos de video)\n"
            "2. Prompts de texto-para-video para cada B-Roll "
            "(em ingles, descritivos, cinematicos)\n"
            "3. Momentos exatos para efeitos sonoros (SFX) nas transicoes\n\n"
            "Retorne um JSON valido com esta estrutura:\n"
            "{\n"
            '  "scenes": [\n'
            "    {\n"
            '      "start_time": 0.0,\n'
            '      "end_time": 6.0,\n'
            '      "description": "descricao semantica da cena",\n'
            '      "broll_prompt": "cinematic prompt in english for '
            'text-to-video generation",\n'
            '      "sfx": "whoosh"\n'
            "    }\n"
            "  ],\n"
            '  "urgent_keywords": ["keyword1", "keyword2"]\n'
            "}\n\n"
            "Regras:\n"
            "- Cada cena deve ter exatamente 6 segundos de duracao\n"
            "- Prompts de B-Roll devem ser em INGLES, cinematicos, detalhados "
            '(ex: "Aerial drone shot of a busy hospital emergency room, '
            'dramatic lighting, 4K")\n'
            '- SFX opcoes: "whoosh", "impact", "ding", "tension_rise", '
            '"news_flash", null\n'
            "- Gere entre 2-5 urgent_keywords relevantes ao topico"
        )

        prompt = system_prompt or default_prompt
        user_msg = f"Roteiro:\n{script}\n\nTimestamps:\n{timestamps}"

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
