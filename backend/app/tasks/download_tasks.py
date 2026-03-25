import uuid
from typing import Optional
from backend.app.core.celery_app import celery_app
from backend.app.core.database import SessionLocal
from backend.app.models.download import DownloadTask, DownloadStatus
from backend.app.core.factory import get_downloader
from backend.app.core.config import settings

@celery_app.task(name="download_task")
def download_task(task_id: str) -> None:
    db = SessionLocal()
    try:
        uid = uuid.UUID(task_id)
        task: Optional[DownloadTask] = db.get(DownloadTask, uid)
        if not task:
            return
        task.status = DownloadStatus.PROCESSING
        db.add(task)
        db.commit()
        db.refresh(task)
        downloader = get_downloader()
        result = downloader.download(task.url, settings.downloads_dir)
        if result.get("status") == "ok":
            task.status = DownloadStatus.COMPLETED
            task.file_path = result.get("file_path")
            task.title = result.get("title")
        else:
            task.status = DownloadStatus.FAILED
        db.add(task)
        db.commit()
    finally:
        db.close()
