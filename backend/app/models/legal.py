"""Legal documents (terms/privacy) and user consent records."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import LegalDocType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class LegalDocument(Base, TimestampMixin):
    __tablename__ = "legal_documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    doc_type: Mapped[LegalDocType] = mapped_column(
        Enum(LegalDocType, name="legal_doc_type"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Only one active document per type is shown to users at a time.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    consents: Mapped[list["UserConsent"]] = relationship(back_populates="document")


class UserConsent(Base):
    __tablename__ = "user_consents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    legal_document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("legal_documents.id", ondelete="RESTRICT")
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="consents")
    document: Mapped["LegalDocument"] = relationship(back_populates="consents")
