from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://app:password@localhost:5432/newstiktok"

    # ── Redis ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── MinIO ─────────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "news-videos"
    MINIO_USE_SSL: bool = False

    # ── GenAIPro ──────────────────────────────────────────────────────
    GENAIPRO_API_KEY: str = ""
    GENAIPRO_BASE_URL: str = "https://genaipro.vn/api"

    # ── OpenRouter ────────────────────────────────────────────────────
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "anthropic/claude-sonnet-4"

    # ── OpenAI (Whisper) ──────────────────────────────────────────────
    OPENAI_API_KEY: str = ""

    # ── JWT ────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Encryption ────────────────────────────────────────────────────
    ENCRYPTION_KEY: str = "change-me-32-byte-key-for-aes256"  # must be exactly 32 bytes

    # ── Pipeline ──────────────────────────────────────────────────────
    MAX_CONCURRENT_VIDEOS: int = 10
    BROLL_COUNT: int = 15
    BROLL_DURATION_SECONDS: int = 6
    BROLL_BATCH_SIZE: int = 10

    # ── noVNC / CDP ───────────────────────────────────────────────────
    NOVNC_URL: str = "http://localhost:6080"
    CDP_URL: str = "http://localhost:9222"

    # ── General ───────────────────────────────────────────────────────
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = {
        "env_file": ("../.env", ".env"),  # Look in parent dir (project root) and current dir
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
