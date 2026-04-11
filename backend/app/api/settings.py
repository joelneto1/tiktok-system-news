import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings as app_settings
from app.database import get_db
from app.models.system_settings import SystemSettings
from app.models.user import User
from app.schemas.settings import SettingBulkUpdate, SettingOut, SettingUpdate
from app.services.minio_client import MinIOClient
from app.utils.activity_log import log_activity
from app.utils.crypto import decrypt_value, encrypt_value

router = APIRouter(prefix="/settings", tags=["settings"])

# Keys that should be auto-encrypted
_SENSITIVE_PATTERNS = ("api_key", "secret", "password")


def _should_encrypt(key: str) -> bool:
    """Return True if the setting key should be stored encrypted."""
    lower = key.lower()
    return any(pat in lower for pat in _SENSITIVE_PATTERNS)


def _mask_value(value: str) -> str:
    """Mask sensitive values, showing only the last 4 characters."""
    if len(value) <= 4:
        return "****"
    return "*" * (len(value) - 4) + value[-4:]


def _setting_to_out(setting: SystemSettings) -> SettingOut:
    """Convert a SystemSettings ORM object to SettingOut, decrypting for display."""
    value = setting.value
    if setting.is_encrypted:
        try:
            value = decrypt_value(value)
        except Exception:
            value = ""

    return SettingOut(
        id=str(setting.id),
        key=setting.key,
        value=value,
        is_encrypted=setting.is_encrypted,
        category=setting.category,
        description=setting.description,
    )


@router.get("/", response_model=list[SettingOut])
async def list_settings(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all settings, optionally filtered by category."""
    query = select(SystemSettings)
    if category:
        query = query.where(SystemSettings.category == category)
    query = query.order_by(SystemSettings.category, SystemSettings.key)

    result = await db.execute(query)
    settings_list = result.scalars().all()
    return [_setting_to_out(s) for s in settings_list]


@router.put("/bulk", response_model=list[SettingOut])
async def bulk_update(
    data: SettingBulkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update multiple settings at once."""
    # Load all existing settings in ONE query
    existing_keys = list(data.settings.keys())
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key.in_(existing_keys))
    )
    existing_map = {s.key: s for s in result.scalars().all()}

    # Update or create in memory (no individual flushes)
    settings_objects = []
    for key, value in data.settings.items():
        is_encrypted = _should_encrypt(key)
        stored_value = encrypt_value(value) if is_encrypted else value

        setting = existing_map.get(key)
        if setting is None:
            setting = SystemSettings(
                key=key,
                value=stored_value,
                is_encrypted=is_encrypted,
                category=key.split("_")[0] if "_" in key else "general",
            )
            db.add(setting)
        else:
            setting.value = stored_value
            setting.is_encrypted = is_encrypted
        settings_objects.append(setting)

    # Single flush for all changes
    await db.flush()

    results: list[SettingOut] = [_setting_to_out(s) for s in settings_objects]
    # Identify which card/section was saved based on keys
    keys = list(data.settings.keys())
    if any("genai" in k or "tts" in k or "voice" in k for k in keys):
        section = "GenAIPro (TTS)"
    elif any("openrouter" in k for k in keys):
        section = "OpenRouter (LLM)"
    elif any("openai" in k or "whisper" in k for k in keys):
        section = "OpenAI (Whisper)"
    elif any("minio" in k for k in keys):
        section = "MinIO (Storage)"
    elif any("language" in k or "broll" in k or "concurrent" in k for k in keys):
        section = "Pipeline"
    else:
        section = "Geral"

    saved_keys = ", ".join(keys)
    await log_activity(db, "SUCCESS", f"[{section}] Configuracoes salvas: {saved_keys}", stage="settings")
    return results


@router.put("/{key}", response_model=SettingOut)
async def update_setting(
    key: str,
    data: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update a setting by key. Auto-encrypts sensitive values."""
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == key)
    )
    setting = result.scalar_one_or_none()

    is_encrypted = _should_encrypt(key)
    stored_value = encrypt_value(data.value) if is_encrypted else data.value

    if setting is None:
        setting = SystemSettings(
            key=key,
            value=stored_value,
            is_encrypted=is_encrypted,
            category=key.split("_")[0] if "_" in key else "general",
        )
        db.add(setting)
    else:
        setting.value = stored_value
        setting.is_encrypted = is_encrypted

    await db.flush()
    await db.refresh(setting)
    await log_activity(db, "INFO", f"Configuracao atualizada: {key}", stage="settings")
    return _setting_to_out(setting)


@router.post("/{key}/test")
async def test_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test connection for a specific setting key."""
    # Fetch the setting value (decrypt if needed)
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == key)
    )
    setting = result.scalar_one_or_none()

    if setting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )

    value = (decrypt_value(setting.value) if setting.is_encrypted else setting.value).strip()

    try:
        if "genai" in key or key == "genaipro_api_key":
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{app_settings.GENAIPRO_BASE_URL}/v1/labs/credits",
                    headers={"Authorization": f"Bearer {value}"},
                )
                resp.raise_for_status()
                data = resp.json()
            await log_activity(db, "SUCCESS", f"Teste GenAIPro: OK - creditos disponiveis", stage="settings")
            return {"status": "ok", "message": f"Conectado! Creditos: {data}"}

        elif "openrouter" in key or key == "openrouter_api_key":
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {value}"},
                )
                resp.raise_for_status()
            await log_activity(db, "SUCCESS", f"Teste OpenRouter: OK", stage="settings")
            return {"status": "ok", "message": "Conectado ao OpenRouter!"}

        elif "openai" in key or key == "openai_api_key":
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {value}"},
                )
                resp.raise_for_status()
            await log_activity(db, "SUCCESS", f"Teste OpenAI: OK", stage="settings")
            return {"status": "ok", "message": "Conectado ao OpenAI!"}

        elif "minio" in key:
            try:
                # Load MinIO settings from DB to test with saved values
                minio_settings = {}
                minio_keys = ["minio_endpoint", "minio_port", "minio_access_key", "minio_secret_key", "minio_bucket", "minio_ssl"]
                for mk in minio_keys:
                    r = await db.execute(select(SystemSettings).where(SystemSettings.key == mk))
                    s = r.scalar_one_or_none()
                    if s:
                        minio_settings[mk] = (decrypt_value(s.value) if s.is_encrypted else s.value).strip()

                from minio import Minio
                endpoint = minio_settings.get("minio_endpoint", app_settings.MINIO_ENDPOINT)
                use_ssl = minio_settings.get("minio_ssl", "false").lower() in ("true", "1", "yes")
                client = Minio(
                    endpoint,
                    access_key=minio_settings.get("minio_access_key", ""),
                    secret_key=minio_settings.get("minio_secret_key", ""),
                    secure=use_ssl,
                )
                bucket = minio_settings.get("minio_bucket", "news-videos")
                import asyncio
                loop = asyncio.get_event_loop()
                exists = await loop.run_in_executor(None, client.bucket_exists, bucket)
                await log_activity(db, "SUCCESS", f"Teste MinIO: OK - bucket '{bucket}' {'existe' if exists else 'nao encontrado'}", stage="settings")
                return {"status": "ok", "message": f"Conectado! Bucket '{bucket}' {'existe' if exists else 'nao encontrado'}"}
            except Exception as exc:
                await log_activity(db, "ERROR", f"Teste MinIO: FALHOU - {str(exc)[:100]}", stage="settings")
                return {"status": "error", "message": str(exc)[:200]}

        else:
            return {"status": "error", "message": f"No test available for key '{key}'"}

    except httpx.HTTPStatusError as exc:
        await log_activity(db, "ERROR", f"Teste de conexao: {key} - FALHOU", stage="settings")
        return {"status": "error", "message": f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"}
    except Exception as exc:
        await log_activity(db, "ERROR", f"Teste de conexao: {key} - FALHOU", stage="settings")
        return {"status": "error", "message": str(exc)}
