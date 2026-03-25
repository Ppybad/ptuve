import os
import subprocess
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
from backend.app.domain.downloader_interface import BaseDownloader

class YtDlpAdapter(BaseDownloader):
    def download(self, url: str, output_path: str) -> Dict[str, Any]:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.netloc:
            return {"status": "error", "file_path": None, "title": None}
        if not output_path:
            return {"status": "error", "file_path": None, "title": None}
        os.makedirs(output_path, exist_ok=True)
        template = os.path.join(output_path, "%(title)s.%(ext)s")
        before = set(os.listdir(output_path))
        cmd: List[str] = [
            "yt-dlp",
            "-f",
            "bestaudio[ext=m4a]",
            "--metadata-from-title",
            "%(artist)s - %(title)s",
            "--extract-audio",
            "-o",
            template,
            url,
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            return {"status": "error", "file_path": None, "title": None}
        if res.returncode != 0:
            return {"status": "error", "file_path": None, "title": None}
        after = set(os.listdir(output_path))
        created = [f for f in (after - before) if f.lower().endswith(".m4a")]
        file_path: Optional[str] = os.path.join(output_path, created[0]) if created else None
        title: Optional[str] = None
        if file_path:
            title = os.path.splitext(os.path.basename(file_path))[0]
        return {"status": "ok", "file_path": file_path, "title": title}
