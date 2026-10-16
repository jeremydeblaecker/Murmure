from abc import ABC, abstractmethod
from pathlib import Path


class TtsEngine(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: Path, voice: str, speed: float) -> Path:
        raise NotImplementedError
