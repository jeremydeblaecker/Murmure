from murmure.text.chunker import chunk_text, split_sentences


def test_split_sentences_keeps_complete_sentences() -> None:
    text = "Bonjour. Comment allez-vous ? Très bien !"
    assert split_sentences(text) == ["Bonjour.", "Comment allez-vous ?", "Très bien !"]


def test_chunk_text_respects_sentence_limit() -> None:
    text = "Un. Deux. Trois. Quatre. Cinq."
    chunks = chunk_text(text, max_chars=500, max_sentences=2)
    assert chunks == ["Un. Deux.", "Trois. Quatre.", "Cinq."]


def test_chunk_text_returns_empty_for_blank_text() -> None:
    assert chunk_text("   ") == []
