import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from backend.app.core.database import Base

class DownloadStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DownloadTask(Base):
    __tablename__ = "download_tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    status = Column(SAEnum(DownloadStatus), nullable=False, default=DownloadStatus.PENDING)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": str(self.id),
            "url": self.url,
            "title": self.title,
            "status": self.status.value if isinstance(self.status, DownloadStatus) else self.status,
            "file_path": self.file_path,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
