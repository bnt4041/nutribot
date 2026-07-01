"""Knowledge-base management endpoints (documents + retrieval debug).

The admin dashboard (Phase 8) will consume these; for now they are the manual
way to load and inspect RAG documents.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.knowledge import KnowledgeDocument
from app.schemas.knowledge import DocumentCreate, DocumentOut, RetrievedChunkOut
from app.services.rag.indexer import index_document
from app.services.rag.retrieval import retrieve

# Knowledge-base management is admin-only.
router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


@router.post(
    "/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED
)
async def create_document(
    payload: DocumentCreate, db: AsyncSession = Depends(get_db)
) -> KnowledgeDocument:
    """Create a document and index it (chunk + embed) synchronously."""
    document = KnowledgeDocument(
        title=payload.title,
        content=payload.content,
        source=payload.source,
        source_url=payload.source_url,
    )
    db.add(document)
    await db.flush()

    try:
        await index_document(db, document)
    except Exception as exc:  # noqa: BLE001
        await db.commit()  # persist FAILED status set by the indexer
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"indexing failed: {exc}",
        ) from exc

    await db.commit()
    await db.refresh(document)
    return document


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db)) -> list[KnowledgeDocument]:
    """List all knowledge documents."""
    result = await db.execute(
        select(KnowledgeDocument).order_by(KnowledgeDocument.id.desc())
    )
    return list(result.scalars().all())


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: int, db: AsyncSession = Depends(get_db)
) -> KnowledgeDocument:
    """Fetch a single document's metadata."""
    document = await db.get(KnowledgeDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return document


@router.post("/documents/{document_id}/reindex", response_model=DocumentOut)
async def reindex_document(
    document_id: int, db: AsyncSession = Depends(get_db)
) -> KnowledgeDocument:
    """Rebuild embeddings for an existing document."""
    document = await db.get(KnowledgeDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    try:
        await index_document(db, document)
    except Exception as exc:  # noqa: BLE001
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"indexing failed: {exc}",
        ) from exc
    await db.commit()
    await db.refresh(document)
    return document


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a document and its embeddings (cascade)."""
    document = await db.get(KnowledgeDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await db.delete(document)
    await db.commit()


@router.get("/search", response_model=list[RetrievedChunkOut])
async def search(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
) -> list[RetrievedChunkOut]:
    """Debug endpoint: run retrieval for a query and return the matches."""
    chunks = await retrieve(db, q)
    return [
        RetrievedChunkOut(
            document_id=c.document_id,
            document_title=c.document_title,
            chunk_text=c.chunk_text,
            similarity=round(c.similarity, 4),
        )
        for c in chunks
    ]
