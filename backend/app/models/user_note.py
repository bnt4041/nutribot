"""Free-form "a tener en cuenta" notes the AI keeps about a user.

These capture preferences and considerations surfaced during conversations
(e.g. "no le gusta la pera") so the assistant can honor and reuse them when
answering or proposing meals. They live in an open section of the profile that
the user can also edit directly.
"""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import NoteCategory
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserNote(Base, TimestampMixin):
    __tablename__ = "user_notes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    category: Mapped[NoteCategory] = mapped_column(
        Enum(NoteCategory, name="note_category"),
        default=NoteCategory.OTHER,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    # Who recorded the note: "ai" or "user".
    source: Mapped[str] = mapped_column(String(16), default="ai", nullable=False)

    user: Mapped["User"] = relationship(back_populates="notes")
