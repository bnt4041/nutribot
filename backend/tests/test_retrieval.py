"""Integration test for cosine retrieval ranking (requires the database)."""

import pytest

from app.db.session import async_session_factory
from app.models.knowledge import EMBEDDING_DIM, KnowledgeDocument, KnowledgeEmbedding
from app.services.rag.retrieval import search_by_vector


def _unit(index: int) -> list[float]:
    """A one-hot vector of the embedding dimension."""
    vec = [0.0] * EMBEDDING_DIM
    vec[index] = 1.0
    return vec


def _mixed() -> list[float]:
    """A normalized vector at ~45 degrees between axes 0 and 1."""
    vec = [0.0] * EMBEDDING_DIM
    vec[0] = vec[1] = 0.7071067811865476
    return vec


@pytest.mark.asyncio
async def test_search_ranks_by_cosine_similarity():
    async with async_session_factory() as session:
        try:
            doc = KnowledgeDocument(title="Test doc", content="irrelevant")
            session.add(doc)
            await session.flush()

            session.add_all(
                [
                    KnowledgeEmbedding(
                        document_id=doc.id, chunk_index=0, chunk_text="A",
                        embedding=_unit(0),
                    ),
                    KnowledgeEmbedding(
                        document_id=doc.id, chunk_index=1, chunk_text="B",
                        embedding=_unit(1),
                    ),
                    KnowledgeEmbedding(
                        document_id=doc.id, chunk_index=2, chunk_text="C",
                        embedding=_mixed(),
                    ),
                ]
            )
            await session.flush()

            # Query aligned with A: expect A (sim=1.0) first, C (~0.707) next,
            # and B (sim=0.0) filtered out by the 0.4 threshold.
            results = await search_by_vector(
                session, _unit(0), top_k=10, min_similarity=0.4
            )
            texts = [r.chunk_text for r in results]

            assert texts[0] == "A"
            assert "B" not in texts
            assert texts.index("A") < texts.index("C")
            assert results[0].similarity == pytest.approx(1.0, abs=1e-4)
        finally:
            await session.rollback()
