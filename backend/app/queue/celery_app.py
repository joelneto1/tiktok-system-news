import platform

from celery import Celery
from app.config import settings

celery_app = Celery(
    "news_pipeline",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Use 'solo' pool on Windows (prefork has permission issues)
# Use 'prefork' on Linux (production)
_pool = "solo" if platform.system() == "Windows" else "prefork"

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_pool=_pool,
    worker_concurrency=1 if _pool == "solo" else settings.MAX_CONCURRENT_VIDEOS,
    broker_connection_retry_on_startup=True,
    task_routes={
        "app.queue.tasks.pipeline_task": {"queue": "pipeline"},
    },
)

celery_app.autodiscover_tasks(["app.queue"])
