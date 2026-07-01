"""Simple, dependency-free text chunking for the RAG pipeline."""

from app.core.config import get_settings

settings = get_settings()


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph/word boundaries.

    Character-based (not token-based) to stay dependency-free; bge-m3 handles
    long inputs, so approximate sizing is fine for retrieval.
    """
    size = chunk_size if chunk_size is not None else settings.rag_chunk_size
    ov = overlap if overlap is not None else settings.rag_chunk_overlap
    if size <= 0:
        raise ValueError("chunk_size must be positive")
    if ov >= size:
        raise ValueError("overlap must be smaller than chunk_size")

    normalized = text.strip()
    if not normalized:
        return []
    if len(normalized) <= size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + size, length)
        # Try to break on a natural boundary near the end of the window.
        if end < length:
            window = normalized[start:end]
            for sep in ("\n\n", "\n", ". ", " "):
                idx = window.rfind(sep)
                # Only honor the boundary if it isn't too early in the window.
                if idx != -1 and idx >= size // 2:
                    end = start + idx + len(sep)
                    break
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(end - ov, start + 1)
    return chunks
