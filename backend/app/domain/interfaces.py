from abc import ABC, abstractmethod
from typing import Dict, Any

class AudioDownloader(ABC):
    @abstractmethod
    def download(self, url: str, output_path: str) -> Dict[str, Any]:
        ...
