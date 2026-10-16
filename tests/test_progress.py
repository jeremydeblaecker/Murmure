from pathlib import Path

from murmure.progress import ProgressStore, ReadingProgress


def test_progress_roundtrip(tmp_path: Path) -> None:
    store = ProgressStore(tmp_path / "progress.json")
    book = tmp_path / "roman.epub"
    book.write_bytes(b"epub")

    progress = ReadingProgress(
        book_id=store.book_id(book),
        path=str(book),
        chapter_index=3,
        chunk_index=7,
        speed=1.05,
    )

    store.save(progress)

    loaded = store.load(book)
    assert loaded is not None
    assert loaded.chapter_index == 3
    assert loaded.chunk_index == 7
    assert loaded.speed == 1.05
