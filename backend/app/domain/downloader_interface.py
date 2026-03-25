from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseDownloader(ABC):
    @abstractmethod
    def download(self, url: str, output_path: str) -> Dict[str, Any]:
        raise NotImplementedError
