from celery import Celery
from backend.app.core.config import settings

celery_app = Celery(
    "ptuve",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.app.tasks.download_tasks"],
)
