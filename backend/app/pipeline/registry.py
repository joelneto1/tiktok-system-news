from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.pipeline.base import BasePipeline

PIPELINE_REGISTRY: dict[str, type[BasePipeline] | None] = {
    "news_tradicional": None,   # Populated on first use
    "news_jornalistico": None,  # Coming soon
    "news_ice": None,           # Coming soon
}


def get_pipeline(model_type: str, job_id: str, video_id: str) -> BasePipeline:
    """Instantiate a pipeline for the given *model_type*.

    Raises ``ValueError`` if the requested pipeline is not yet available.
    """
    # Lazy import to avoid circular dependencies
    if PIPELINE_REGISTRY["news_tradicional"] is None:
        from app.pipeline.news_tradicional.pipeline import NewsTradicionalPipeline

        PIPELINE_REGISTRY["news_tradicional"] = NewsTradicionalPipeline

    pipeline_cls = PIPELINE_REGISTRY.get(model_type)
    if pipeline_cls is None:
        raise ValueError(f"Pipeline '{model_type}' is not available yet")

    return pipeline_cls(job_id=job_id, video_id=video_id)
