from backend.app.domain.downloader_interface import BaseDownloader
from backend.app.infrastructure.ytdlp_adapter import YtDlpAdapter
from backend.app.core.config import settings

def get_downloader() -> BaseDownloader:
    t = settings.downloader_type.lower()
    if t == "ytdlp":
        return YtDlpAdapter()
    raise ValueError("DOWNLOADER_TYPE no soportado")
