import hashlib
from pathlib import Path


class AudioCache:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(".cache") / "murmure"
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, text: str, engine: str, voice: str, speed: float) -> Path:
        payload = f"{engine}|{voice}|{speed:.3f}|{text}".encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return self.root / f"{digest}.wav"
