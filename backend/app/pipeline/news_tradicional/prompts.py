"""System prompt keys used by the News Tradicional pipeline.

Cada modelo de video tem 2 prompts:
- Roteirista: gera o roteiro de narracao
- Diretor de Cena: segmenta em cenas, gera broll_prompts e define SFX
"""

PROMPT_KEYS = {
    "screenwriter": {
        "key": "news_tradicional_roteirista",
        "name": "Roteirista",
        "description": "Prompt para gerar o roteiro de narracao do video",
        "model_type": "news_tradicional",
    },
    "scene_director": {
        "key": "news_tradicional_diretor_cena",
        "name": "Diretor de Cena",
        "description": "Prompt para segmentar o roteiro em cenas, gerar prompts de B-Roll e definir SFX",
        "model_type": "news_tradicional",
    },
}
