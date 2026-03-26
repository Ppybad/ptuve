import os
import uuid
from typing import List, Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from backend.app.core.database import get_db
from backend.app.models.download import DownloadTask, DownloadStatus
from backend.app.tasks.download_tasks import download_task
from backend.app.core.tidal_auth import tidal_status

router = APIRouter()

class DownloadCreate(BaseModel):
    url: HttpUrl

@router.post("/downloads")
def create_download(payload: DownloadCreate, db: Session = Depends(get_db)) -> Dict[str, Any]:
    task = DownloadTask(url=str(payload.url), status=DownloadStatus.PENDING)
    db.add(task)
    db.commit()
    db.refresh(task)
    download_task.delay(str(task.id))
    return task.to_dict()

@router.get("/downloads")
def list_downloads(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if skip < 0:
        skip = 0
    if limit <= 0:
        limit = 10
    base_q = db.query(DownloadTask)
    if status:
        st = status.upper()
        try:
            st_enum = DownloadStatus(st)
            base_q = base_q.filter(DownloadTask.status == st_enum)
        except ValueError:
            pass
    if search:
        like = f"%{search}%"
        base_q = base_q.filter(or_(DownloadTask.title.ilike(like), DownloadTask.url.ilike(like)))
    total = base_q.with_entities(func.count(DownloadTask.id)).scalar() or 0
    tasks = base_q.order_by(DownloadTask.created_at.desc()).offset(skip).limit(limit).all()
    items = [t.to_dict() for t in tasks]
    return {"items": items, "total": total, "skip": skip, "limit": limit, "has_more": skip + limit < total}

@router.get("/downloads/{task_id}")
def get_download(task_id: uuid.UUID, db: Session = Depends(get_db)) -> Dict[str, Any]:
    task = db.get(DownloadTask, task_id)
    if not task:
        raise HTTPException(status_code=404)
    return task.to_dict()

@router.post("/downloads/{task_id}/retry")
def retry_download(task_id: uuid.UUID, db: Session = Depends(get_db)) -> Dict[str, Any]:
    task = db.get(DownloadTask, task_id)
    if not task:
        raise HTTPException(status_code=404)
    if task.status in (DownloadStatus.PENDING, DownloadStatus.PROCESSING):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    if task.status != DownloadStatus.FAILED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    task.status = DownloadStatus.PENDING
    task.file_path = None
    task.title = None
    db.add(task)
    db.commit()
    db.refresh(task)
    download_task.delay(str(task.id))
    return task.to_dict()

@router.delete("/downloads/{task_id}")
def delete_download(task_id: uuid.UUID, db: Session = Depends(get_db)) -> Dict[str, Any]:
    task = db.get(DownloadTask, task_id)
    if not task:
        raise HTTPException(status_code=404)
    if task.status == DownloadStatus.COMPLETED and task.file_path:
        try:
            if os.path.isfile(task.file_path):
                os.remove(task.file_path)
        except OSError:
            pass
    db.delete(task)
    db.commit()
    return {"id": str(task_id), "deleted": True}

@router.get("/downloads/{task_id}/file")
def get_download_file(task_id: uuid.UUID, db: Session = Depends(get_db)):
    task = db.get(DownloadTask, task_id)
    if not task:
        raise HTTPException(status_code=404)
    if not task.file_path or not os.path.isfile(task.file_path):
        raise HTTPException(status_code=404)
    filename = os.path.basename(task.file_path)
    ext = os.path.splitext(filename)[1].lower()
    media_type = "application/octet-stream"
    if ext == ".mp3":
        media_type = "audio/mpeg"
    elif ext == ".m4a" or ext == ".aac":
        media_type = "audio/mp4"
    elif ext == ".flac":
        media_type = "audio/flac"
    return FileResponse(task.file_path, media_type=media_type, filename=filename)

@router.get("/tidal/status")
def get_tidal_status() -> Dict[str, str]:
    return {"status": tidal_status()}
