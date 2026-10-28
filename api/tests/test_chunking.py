from app.embeddings import chunk_text


def test_blank_lines_are_ignored():
    assert chunk_text("a\n\n\nb") == ["a\nb"]


def test_long_text_is_split_under_the_limit():
    text = "\n".join(["x" * 90] * 5)
    chunks = chunk_text(text, max_chars=200)
    assert all(len(c) <= 200 for c in chunks)
    assert len(chunks) == 3
