"""Tests for the reminders/notifications service (avisos y recordatorios)."""

from datetime import date, datetime, time

import pytest

from app.db.session import async_session_factory
from app.models.enums import ReminderType, UserRole
from app.models.reminder import Reminder
from app.models.user import User
from app.services import reminders
from app.services.reminders import ReminderValidationError


def test_type_coercion():
    assert reminders._to_type("meal") == ReminderType.MEAL
    assert reminders._to_type("WATER") == ReminderType.WATER
    with pytest.raises(ReminderValidationError):
        reminders._to_type("nonsense")


def test_time_coercion():
    assert reminders._to_time("09:05") == time(9, 5)
    assert reminders._to_time(time(8, 0)) == time(8, 0)
    with pytest.raises(ReminderValidationError):
        reminders._to_time("not-a-time")


def test_days_of_week_coercion():
    assert reminders._to_days_of_week(None) == []
    assert reminders._to_days_of_week([3, 1, 1]) == [1, 3]
    with pytest.raises(ReminderValidationError):
        reminders._to_days_of_week([0, 7])


def test_reminders_summary_lines_skip_disabled():
    active = Reminder(type=ReminderType.WATER, time=time(12, 0), days_of_week=[], enabled=True)
    disabled = Reminder(type=ReminderType.MEAL, time=time(9, 0), days_of_week=[0, 2], enabled=False)
    lines = reminders.reminders_summary_lines([active, disabled])
    assert len(lines) == 1
    assert "Beber agua" in lines[0]
    assert "12:00" in lines[0]


@pytest.mark.parametrize(
    "reminder_kwargs,now,expected",
    [
        # Fires: enabled, no day restriction, exact minute match.
        (dict(enabled=True, time=time(9, 0), days_of_week=[], last_sent_on=None), datetime(2026, 7, 6, 9, 0), True),
        # Disabled reminders never fire.
        (dict(enabled=False, time=time(9, 0), days_of_week=[], last_sent_on=None), datetime(2026, 7, 6, 9, 0), False),
        # Already sent today: skip even if the time matches.
        (dict(enabled=True, time=time(9, 0), days_of_week=[], last_sent_on=date(2026, 7, 6)), datetime(2026, 7, 6, 9, 0), False),
        # Weekday restriction excludes today (2026-07-06 is a Monday = 0).
        (dict(enabled=True, time=time(9, 0), days_of_week=[2], last_sent_on=None), datetime(2026, 7, 6, 9, 0), False),
        # Weekday restriction includes today.
        (dict(enabled=True, time=time(9, 0), days_of_week=[0], last_sent_on=None), datetime(2026, 7, 6, 9, 0), True),
        # Wrong minute.
        (dict(enabled=True, time=time(9, 0), days_of_week=[], last_sent_on=None), datetime(2026, 7, 6, 9, 1), False),
    ],
)
def test_is_due(reminder_kwargs, now, expected):
    reminder = Reminder(**reminder_kwargs)
    assert reminders.is_due(reminder, now) is expected


@pytest.mark.asyncio
async def test_create_custom_reminder_requires_message():
    async with async_session_factory() as session:
        try:
            user = User(telegram_id=940001, role=UserRole.CLIENT)
            session.add(user)
            await session.flush()

            with pytest.raises(ReminderValidationError):
                await reminders.create_reminder(session, user, type="custom", time="09:00")

            reminder = await reminders.create_reminder(
                session, user, type="custom", time="09:00", message="tómate la vitamina"
            )
            assert reminder.message == "tómate la vitamina"
        finally:
            await session.rollback()


@pytest.mark.asyncio
async def test_create_list_update_delete_reminder():
    async with async_session_factory() as session:
        try:
            user = User(telegram_id=940002, role=UserRole.CLIENT)
            session.add(user)
            await session.flush()

            reminder = await reminders.create_reminder(
                session, user, type="water", time="12:00", days_of_week=[1, 3]
            )
            assert reminder.days_of_week == [1, 3]
            assert reminder.message is None
            assert reminders.reminder_to_dict(reminder)["message"] == reminders.DEFAULT_MESSAGES[ReminderType.WATER]

            listed = await reminders.list_reminders(session, user)
            assert [r.id for r in listed] == [reminder.id]

            updated = await reminders.update_reminder(session, reminder, time="13:30", enabled=False)
            assert updated.time == time(13, 30)
            assert updated.enabled is False

            await reminders.delete_reminder(session, reminder)
            assert await reminders.list_reminders(session, user) == []
        finally:
            await session.rollback()


@pytest.mark.asyncio
async def test_get_reminder_scoped_to_owner():
    async with async_session_factory() as session:
        try:
            owner = User(telegram_id=940003, role=UserRole.CLIENT)
            other = User(telegram_id=940004, role=UserRole.CLIENT)
            session.add_all([owner, other])
            await session.flush()

            reminder = await reminders.create_reminder(session, owner, type="meal", time="08:00")
            assert await reminders.get_reminder(session, other, reminder.id) is None
            assert await reminders.get_reminder(session, owner, reminder.id) is not None
        finally:
            await session.rollback()
