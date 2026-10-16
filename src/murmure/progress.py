import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ReadingProgress:
    book_id: str
    path: str
    chapter_index: int = 0
    chunk_index: int = 0
    speed: float = 1.0


class ProgressStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(".cache") / "murmure" / "progress.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def book_id(path: str | Path) -> str:
        resolved = str(Path(path).resolve()).encode("utf-8")
        return hashlib.sha256(resolved).hexdigest()

    def load(self, path: str | Path) -> ReadingProgress | None:
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            book_id = self.book_id(path)
            raw = data.get(book_id)
            if not raw:
                return None
            return ReadingProgress(**raw)
        except (OSError, ValueError, TypeError):
            return None

    def save(self, progress: ReadingProgress) -> None:
        data: dict[str, dict] = {}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                data = {}

        data[progress.book_id] = asdict(progress)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
