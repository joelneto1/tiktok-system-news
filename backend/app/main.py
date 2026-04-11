from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.seeds.prompts import seed_default_prompts
from app.services.minio_client import minio_client
from app.utils.logger import setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logger(settings.LOG_LEVEL)
    minio_client.ensure_bucket()
    await seed_default_prompts()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="News TikTok Pipeline",
    version="1.0.0",
    lifespan=lifespan,
    # redirect_slashes defaults to True — routes work with or without trailing slash
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
