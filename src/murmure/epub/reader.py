from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import ITEM_DOCUMENT, epub


@dataclass(frozen=True)
class Chapter:
    title: str
    text: str


def _clean_html(content: bytes) -> str:
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["script", "style", "nav"]):
        tag.decompose()

    blocks: list[str] = []
    for element in soup.find_all(["h1", "h2", "h3", "p", "blockquote", "li"]):
        text = " ".join(element.get_text(" ", strip=True).split())
        if text:
            blocks.append(text)

    if blocks:
        return "\n\n".join(blocks)

    return " ".join(soup.get_text(" ", strip=True).split())


def load_epub(path: str | Path) -> list[Chapter]:
    book = epub.read_epub(str(path))
    chapters: list[Chapter] = []

    for index, item in enumerate(book.get_items_of_type(ITEM_DOCUMENT), start=1):
        text = _clean_html(item.get_content())
        if not text:
            continue

        title = item.get_name()
        try:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            heading = soup.find(["h1", "h2", "h3"])
            if heading:
                candidate = " ".join(heading.get_text(" ", strip=True).split())
                if candidate:
                    title = candidate
        except Exception:
            pass

        chapters.append(Chapter(title=title or f"Chapitre {index}", text=text))

    return chapters
