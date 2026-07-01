"""Legal consent: fetch the active terms and record user acceptance."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import LegalDocType
from app.models.legal import LegalDocument, UserConsent
from app.models.user import User


async def get_active_terms(db: AsyncSession) -> LegalDocument | None:
    """Return the active terms document, if any."""
    result = await db.execute(
        select(LegalDocument)
        .where(
            LegalDocument.doc_type == LegalDocType.TERMS,
            LegalDocument.is_active.is_(True),
        )
        .order_by(LegalDocument.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def has_accepted(db: AsyncSession, user: User, document: LegalDocument) -> bool:
    """Whether the user has already accepted the given document."""
    result = await db.execute(
        select(UserConsent.id).where(
            UserConsent.user_id == user.id,
            UserConsent.legal_document_id == document.id,
        )
    )
    return result.first() is not None


async def record_consent(
    db: AsyncSession, user: User, document: LegalDocument
) -> None:
    """Persist that the user accepted the document (idempotent-ish)."""
    if await has_accepted(db, user, document):
        return
    db.add(UserConsent(user_id=user.id, legal_document_id=document.id))
    await db.flush()
