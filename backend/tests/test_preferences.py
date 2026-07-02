"""Tests for the "a tener en cuenta" user notes service."""

import pytest

from app.db.session import async_session_factory
from app.models.enums import NoteCategory, UserRole
from app.models.user import User
from app.models.user_note import UserNote
from app.services import preferences


def test_category_coercion_defaults_to_other():
    assert preferences._to_category("dislike") == NoteCategory.DISLIKE
    assert preferences._to_category("MEDICAL") == NoteCategory.MEDICAL
    assert preferences._to_category("nonsense") == NoteCategory.OTHER
    assert preferences._to_category(None) == NoteCategory.OTHER
    assert preferences._to_category(NoteCategory.LIKE) == NoteCategory.LIKE


def test_notes_summary_lines_include_category_label():
    notes = [
        UserNote(category=NoteCategory.DISLIKE, content="no le gusta la pera"),
        UserNote(category=NoteCategory.MEDICAL, content="hipertensión"),
    ]
    lines = preferences.notes_summary_lines(notes)
    assert lines[0] == "- [No le gusta / evita] no le gusta la pera"
    assert lines[1] == "- [Salud] hipertensión"


@pytest.mark.asyncio
async def test_add_list_and_delete_notes():
    async with async_session_factory() as session:
        try:
            user = User(telegram_id=930005, role=UserRole.CLIENT)
            session.add(user)
            await session.flush()

            note = await preferences.add_note(
                session, user, content="no le gusta la pera", category="dislike"
            )
            assert note.category == NoteCategory.DISLIKE
            assert note.source == "ai"

            listed = await preferences.list_notes(session, user)
            assert [n.content for n in listed] == ["no le gusta la pera"]

            assert preferences.note_to_dict(note)["category"] == "dislike"

            await preferences.delete_note(session, note)
            assert await preferences.list_notes(session, user) == []
        finally:
            await session.rollback()


@pytest.mark.asyncio
async def test_get_note_scoped_to_owner():
    async with async_session_factory() as session:
        try:
            owner = User(telegram_id=930006, role=UserRole.CLIENT)
            other = User(telegram_id=930007, role=UserRole.CLIENT)
            session.add_all([owner, other])
            await session.flush()

            note = await preferences.add_note(session, owner, content="vegano")
            assert await preferences.get_note(session, other, note.id) is None
            assert await preferences.get_note(session, owner, note.id) is not None
        finally:
            await session.rollback()
