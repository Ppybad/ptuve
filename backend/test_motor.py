import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.core.factory import get_downloader
from backend.app.core.config import settings

def main() -> None:
    test_url = os.environ.get("TEST_URL", "https://www.youtube.com/watch?v=HW3D8SiiCs8")
    downloader = get_downloader()
    output_path = settings.downloads_dir
    try:
        result = downloader.download(test_url, output_path)
    except Exception as e:
        print(f"status=error")
        print(f"error={e}")
        return
    status = result.get("status")
    file_path = result.get("file_path")
    title = result.get("title")
    exists = isinstance(file_path, str) and file_path.endswith(".m4a") and os.path.isfile(file_path)
    print(f"status={status}")
    print(f"title={title}")
    print(f"file_path={file_path}")
    print(f"exists_m4a={exists}")

if __name__ == "__main__":
    main()
