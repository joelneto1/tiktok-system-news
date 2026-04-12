import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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


# ── Serve frontend SPA ──────────────────────────────────────────
_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
_frontend_dist = os.path.normpath(_frontend_dist)

if os.path.isdir(_frontend_dist):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(_frontend_dist, "assets")),
        name="static-assets",
    )

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API routes: redirect to trailing slash so FastAPI router matches
        if full_path.startswith("api/") or full_path == "api":
            from fastapi.responses import RedirectResponse
            from starlette.requests import Request
            # Let FastAPI's own routing handle it by returning 404
            # The API client should use trailing slashes
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")

        file_path = os.path.join(_frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_frontend_dist, "index.html"))
