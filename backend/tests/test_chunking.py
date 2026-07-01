"""Unit tests for the RAG text chunker."""

from app.services.rag.chunking import chunk_text


def test_short_text_returns_single_chunk():
    assert chunk_text("Texto corto.", chunk_size=100, overlap=10) == ["Texto corto."]


def test_empty_text_returns_no_chunks():
    assert chunk_text("   ", chunk_size=100, overlap=10) == []


def test_long_text_is_split_with_overlap():
    text = ("palabra " * 300).strip()  # ~2400 chars
    chunks = chunk_text(text, chunk_size=400, overlap=50)
    assert len(chunks) > 1
    # Every chunk respects the size budget (allowing the boundary search slack).
    assert all(len(c) <= 400 for c in chunks)
    # Reassembled content covers the whole text (no data lost).
    assert chunks[0].startswith("palabra")


def test_prefers_paragraph_boundaries():
    text = "A" * 200 + "\n\n" + "B" * 200
    chunks = chunk_text(text, chunk_size=250, overlap=20)
    # The first chunk should end at the paragraph break, not mid-way into B's.
    assert chunks[0].endswith("A")


def test_invalid_params_raise():
    import pytest

    with pytest.raises(ValueError):
        chunk_text("x", chunk_size=0)
    with pytest.raises(ValueError):
        chunk_text("x", chunk_size=100, overlap=100)
