from celery import Celery
from backend.app.core.config import settings
from backend.app.core.tidal_auth import ensure_session_and_start_device_login_if_needed

celery_app = Celery(
    "ptuve",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.app.tasks.download_tasks", "backend.app.tasks.tidal_tasks"],
)

ensure_session_and_start_device_login_if_needed()
