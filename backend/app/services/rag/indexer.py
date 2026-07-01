"""Document indexing: chunk -> embed -> store embeddings."""

import hashlib
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import DocumentStatus
from app.models.knowledge import KnowledgeDocument, KnowledgeEmbedding
from app.services.rag.chunking import chunk_text
from app.services.rag.embeddings import embed_texts


def content_hash(content: str) -> str:
    """Stable hash of document content, for dedupe/change detection."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def index_document(db: AsyncSession, document: KnowledgeDocument) -> int:
    """(Re)build embeddings for a document. Returns the number of chunks.

    Existing embeddings for the document are removed first, so this is safe to
    call again after the content changes.
    """
    await db.execute(
        delete(KnowledgeEmbedding).where(
            KnowledgeEmbedding.document_id == document.id
        )
    )

    chunks = chunk_text(document.content)
    try:
        vectors = await embed_texts(chunks)
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            db.add(
                KnowledgeEmbedding(
                    document_id=document.id,
                    chunk_index=index,
                    chunk_text=chunk,
                    embedding=vector,
                )
            )
        document.chunk_count = len(chunks)
        document.status = DocumentStatus.INDEXED
        document.indexed_at = datetime.now(timezone.utc)
    except Exception:
        document.status = DocumentStatus.FAILED
        raise
    finally:
        document.content_hash = content_hash(document.content)

    await db.flush()
    return len(chunks)
