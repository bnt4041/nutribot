"""User notes ("a tener en cuenta"): CRUD shared by the API and the AI tool."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NoteCategory
from app.models.user import User
from app.models.user_note import UserNote

CATEGORY_ES = {
    NoteCategory.DISLIKE: "No le gusta / evita",
    NoteCategory.LIKE: "Le gusta",
    NoteCategory.MEDICAL: "Salud",
    NoteCategory.HABIT: "Hábito",
    NoteCategory.OTHER: "Otro",
}


def _to_category(value) -> NoteCategory:
    if isinstance(value, NoteCategory):
        return value
    if not value:
        return NoteCategory.OTHER
    try:
        return NoteCategory(str(value).strip().lower())
    except ValueError:
        return NoteCategory.OTHER


async def list_notes(db: AsyncSession, user: User) -> list[UserNote]:
    result = await db.execute(
        select(UserNote)
        .where(UserNote.user_id == user.id)
        .order_by(UserNote.category, UserNote.id)
    )
    return list(result.scalars().all())


async def add_note(
    db: AsyncSession,
    user: User,
    *,
    content: str,
    category=NoteCategory.OTHER,
    source: str = "ai",
) -> UserNote:
    note = UserNote(
        user_id=user.id,
        content=content.strip(),
        category=_to_category(category),
        source=source,
    )
    db.add(note)
    await db.flush()
    return note


async def get_note(db: AsyncSession, user: User, note_id: int) -> UserNote | None:
    note = await db.get(UserNote, note_id)
    if note is None or note.user_id != user.id:
        return None
    return note


async def delete_note(db: AsyncSession, note: UserNote) -> None:
    await db.delete(note)
    await db.flush()


def note_to_dict(note: UserNote) -> dict:
    return {
        "id": note.id,
        "category": note.category.value,
        "content": note.content,
        "source": note.source,
    }


def notes_summary_lines(notes: list[UserNote]) -> list[str]:
    """Lines describing the notes for the system prompt."""
    return [f"- [{CATEGORY_ES.get(n.category, 'Otro')}] {n.content}" for n in notes]
