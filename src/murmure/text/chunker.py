import re

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÀ-ÖØ-Þ0-9«“—])")


def split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"[ \t]+", " ", text.strip())
    if not normalized:
        return []

    sentences: list[str] = []
    for paragraph in re.split(r"\n\s*\n", normalized):
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        parts = _SENTENCE_END.split(paragraph)
        sentences.extend(part.strip() for part in parts if part.strip())

    return sentences


def chunk_text(text: str, max_chars: int = 420, max_sentences: int = 4) -> list[str]:
    sentences = split_sentences(text)
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0

    for sentence in sentences:
        projected = current_size + len(sentence) + (1 if current else 0)
        if current and (projected > max_chars or len(current) >= max_sentences):
            chunks.append(" ".join(current))
            current = []
            current_size = 0

        if len(sentence) > max_chars:
            words = sentence.split()
            buffer: list[str] = []
            buffer_size = 0
            for word in words:
                projected_word = buffer_size + len(word) + (1 if buffer else 0)
                if buffer and projected_word > max_chars:
                    if current:
                        chunks.append(" ".join(current))
                        current = []
                        current_size = 0
                    chunks.append(" ".join(buffer))
                    buffer = []
                    buffer_size = 0
                buffer.append(word)
                buffer_size += len(word) + (1 if len(buffer) > 1 else 0)

            if buffer:
                current = buffer
                current_size = buffer_size
            continue

        current.append(sentence)
        current_size = projected

    if current:
        chunks.append(" ".join(current))

    return chunks
