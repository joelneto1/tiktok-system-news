from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.system_prompt import SystemPrompt
from app.models.user import User
from app.schemas.prompt import PromptCreate, PromptOut, PromptUpdate
from app.utils.activity_log import log_activity

router = APIRouter(prefix="/prompts", tags=["prompts"])


def _prompt_to_out(prompt: SystemPrompt) -> PromptOut:
    return PromptOut(
        id=str(prompt.id),
        key=prompt.key,
        name=prompt.name,
        description=prompt.description,
        content=prompt.content,
        model_type=prompt.model_type,
        is_active=prompt.is_active,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )


@router.get("/", response_model=list[PromptOut])
async def list_prompts(
    model_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all prompts, optionally filtered by model_type."""
    query = select(SystemPrompt)
    if model_type:
        query = query.where(SystemPrompt.model_type == model_type)
    query = query.order_by(SystemPrompt.key)

    result = await db.execute(query)
    prompts = result.scalars().all()
    return [_prompt_to_out(p) for p in prompts]


@router.get("/{key}", response_model=PromptOut)
async def get_prompt(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single prompt by key."""
    result = await db.execute(
        select(SystemPrompt).where(SystemPrompt.key == key)
    )
    prompt = result.scalar_one_or_none()
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{key}' not found",
        )
    return _prompt_to_out(prompt)


@router.post("/", response_model=PromptOut, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    data: PromptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new prompt."""
    # Check for duplicate key
    result = await db.execute(
        select(SystemPrompt).where(SystemPrompt.key == data.key)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Prompt with key '{data.key}' already exists",
        )

    prompt = SystemPrompt(
        key=data.key,
        name=data.name,
        description=data.description,
        content=data.content,
        model_type=data.model_type,
    )
    db.add(prompt)
    await db.flush()
    await db.refresh(prompt)
    await log_activity(db, "INFO", f"System prompt criado: {data.key}", stage="prompts")
    return _prompt_to_out(prompt)


@router.put("/{key}", response_model=PromptOut)
async def update_prompt(
    key: str,
    data: PromptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the content of an existing prompt."""
    result = await db.execute(
        select(SystemPrompt).where(SystemPrompt.key == key)
    )
    prompt = result.scalar_one_or_none()
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{key}' not found",
        )

    prompt.content = data.content
    await db.flush()
    await db.refresh(prompt)
    await log_activity(db, "SUCCESS", f"System prompt atualizado: {key}", stage="prompts")
    return _prompt_to_out(prompt)


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a prompt by key."""
    result = await db.execute(
        select(SystemPrompt).where(SystemPrompt.key == key)
    )
    prompt = result.scalar_one_or_none()
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{key}' not found",
        )

    await db.delete(prompt)
    await db.flush()
    await log_activity(db, "WARNING", f"System prompt excluido: {key}", stage="prompts")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
