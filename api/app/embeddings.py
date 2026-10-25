from fastembed import TextEmbedding

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = TextEmbedding(EMBED_MODEL, cache_dir="/models")
    return _model


def embed_passages(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _get_model().passage_embed(texts)]


def embed_query(text: str) -> list[float]:
    return next(iter(_get_model().query_embed(text))).tolist()


def chunk_text(text: str, max_chars: int = 200) -> list[str]:
    chunks, current = [], ""
    for line in (l.strip() for l in text.splitlines()):
        if not line:
            continue
        if current and len(current) + len(line) + 1 > max_chars:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks
