import httpx
from fastapi import APIRouter, HTTPException, Query, status

from app.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/voices", tags=["voices"])


@router.get("/")
async def list_voices(
    language: str | None = Query(None),
    category: str | None = Query(None),
    page: int = Query(0, ge=0),
    page_size: int = Query(30, ge=1, le=100),
):
    """Proxy to GenAIPro API to list available TTS voices."""
    if not settings.GENAIPRO_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GenAIPro API key is not configured",
        )

    params: dict = {
        "page": page,
        "page_size": page_size,
    }
    if language:
        params["language"] = language
    if category:
        params["category"] = category

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{settings.GENAIPRO_BASE_URL}/v1/labs/voices",
                params=params,
                headers={
                    "Authorization": f"Bearer {settings.GENAIPRO_API_KEY}",
                    "Accept": "application/json",
                },
            )

        if response.status_code != 200:
            logger.warning(
                f"GenAIPro voices API returned status {response.status_code}: {response.text}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GenAIPro API returned status {response.status_code}",
            )

        return response.json()

    except httpx.RequestError as exc:
        logger.error(f"Failed to reach GenAIPro API: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach GenAIPro voice service",
        )
