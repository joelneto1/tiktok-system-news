from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.api.references import router as references_router
from app.api.videos import router as videos_router
from app.api.voices import router as voices_router
from app.api.settings import router as settings_router
from app.api.prompts import router as prompts_router
from app.api.connections import router as connections_router
from app.api.logs import router as logs_router
from app.api.storage import router as storage_router
from app.api.audios import router as audios_router
from app.api.sfx import router as sfx_router
from app.api.pipeline import router as pipeline_router
from app.api.websocket import router as ws_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(references_router)
api_router.include_router(videos_router)
api_router.include_router(voices_router)
api_router.include_router(settings_router)
api_router.include_router(prompts_router)
api_router.include_router(connections_router)
api_router.include_router(logs_router)
api_router.include_router(storage_router)
api_router.include_router(audios_router)
api_router.include_router(sfx_router)
api_router.include_router(pipeline_router)
api_router.include_router(ws_router)
