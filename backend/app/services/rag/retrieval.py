"""Similarity retrieval over knowledge embeddings (pgvector cosine)."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.knowledge import KnowledgeDocument, KnowledgeEmbedding
from app.services.rag.embeddings import embed_query

settings = get_settings()


@dataclass
class RetrievedChunk:
    document_id: int
    document_title: str
    chunk_text: str
    similarity: float


async def search_by_vector(
    db: AsyncSession,
    query_vec: list[float],
    top_k: int | None = None,
    min_similarity: float | None = None,
) -> list[RetrievedChunk]:
    """Cosine top-k search for a precomputed query vector.

    Split out from ``retrieve`` so ranking can be tested without the embeddings
    service. Cosine distance (``<=>``) is used; similarity = 1 - distance.
    """
    k = top_k or settings.rag_top_k
    threshold = (
        min_similarity if min_similarity is not None else settings.rag_min_similarity
    )

    distance = KnowledgeEmbedding.embedding.cosine_distance(query_vec)

    result = await db.execute(
        select(
            KnowledgeEmbedding.document_id,
            KnowledgeDocument.title,
            KnowledgeEmbedding.chunk_text,
            distance.label("distance"),
        )
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeEmbedding.document_id)
        .order_by(distance)
        .limit(k)
    )

    chunks: list[RetrievedChunk] = []
    for document_id, title, chunk_text, dist in result.all():
        similarity = 1.0 - float(dist)
        if similarity >= threshold:
            chunks.append(
                RetrievedChunk(
                    document_id=document_id,
                    document_title=title,
                    chunk_text=chunk_text,
                    similarity=similarity,
                )
            )
    return chunks


async def retrieve(
    db: AsyncSession,
    query: str,
    top_k: int | None = None,
    min_similarity: float | None = None,
) -> list[RetrievedChunk]:
    """Embed the query and return the most similar chunks above the threshold."""
    query_vec = await embed_query(query)
    return await search_by_vector(db, query_vec, top_k, min_similarity)


def build_context_block(chunks: list[RetrievedChunk]) -> str | None:
    """Format retrieved chunks as a context block for the system prompt."""
    if not chunks:
        return None
    parts = [
        f"[{c.document_title}] {c.chunk_text}" for c in chunks
    ]
    body = "\n\n".join(parts)
    return (
        "\n\nInformación de la base de conocimiento (úsala si es relevante para la "
        "pregunta; si no lo es, ignórala):\n" + body
    )
