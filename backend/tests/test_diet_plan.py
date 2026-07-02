"""Tests for the recommended diet plan service (concrete dates)."""

from datetime import date, time, timedelta

import pytest

from app.db.session import async_session_factory
from app.models.enums import DietItemStatus, MealType, UserRole
from app.models.user import User
from app.services.nutrition import diet_plan


def test_next_weekday_date_picks_nearest_upcoming():
    monday = date(2026, 7, 6)  # a Monday
    # Same weekday resolves to the same day (>= from_date).
    assert diet_plan.next_weekday_date(0, monday) == monday
    # Friday (4) after that Monday is 4 days ahead.
    assert diet_plan.next_weekday_date(4, monday) == monday + timedelta(days=4)
    # Sunday (6) is 6 days ahead.
    assert diet_plan.next_weekday_date(6, monday) == monday + timedelta(days=6)


def test_resolve_date_from_explicit_and_weekday():
    assert diet_plan.resolve_date("2026-07-10") == date(2026, 7, 10)
    assert diet_plan.resolve_date("10/07/2026") == date(2026, 7, 10)
    assert diet_plan.resolve_date(None, None) is None
    # A weekday hint yields an upcoming date with that weekday.
    resolved = diet_plan.resolve_date(None, 4)  # Friday
    assert resolved is not None and resolved.weekday() == 4
    assert resolved >= date.today()


def test_coercion_helpers():
    assert diet_plan._to_time("08:30") == time(8, 30)
    assert diet_plan._to_time("nope") is None
    assert diet_plan._to_meal_type("breakfast") == MealType.BREAKFAST
    assert diet_plan._to_meal_type("brunch") is None


def test_plan_summary_lines_are_readable():
    items = [
        diet_plan.DietPlanItem(
            scheduled_date=date(2026, 7, 6),  # Monday
            meal_type=MealType.BREAKFAST,
            scheduled_time=time(8, 0),
            title="Avena con fruta",
            status=DietItemStatus.PROPOSED,
        ),
        diet_plan.DietPlanItem(
            scheduled_date=None,
            meal_type=None,
            title="Batido",
            status=DietItemStatus.CONFIRMED,
        ),
    ]
    lines = diet_plan.plan_summary_lines(items)
    assert lines[0] == "- Lunes 2026-07-06 Desayuno 08:00: Avena con fruta (propuesta)"
    assert lines[1] == "- Batido (confirmada)"


@pytest.mark.asyncio
async def test_add_list_confirm_and_delete():
    async with async_session_factory() as session:
        try:
            user = User(telegram_id=920002, role=UserRole.CLIENT)
            session.add(user)
            await session.flush()

            item = await diet_plan.add_item(
                session,
                user,
                title="Pollo con arroz",
                scheduled_date="2026-07-10",
                meal_type="lunch",
                scheduled_time="14:00",
                calories="600",
            )
            assert item.status == DietItemStatus.PROPOSED
            assert item.source == "ai"
            assert item.scheduled_date == date(2026, 7, 10)
            assert item.meal_type == MealType.LUNCH
            assert item.scheduled_time == time(14, 0)

            listed = await diet_plan.list_items(session, user)
            assert [i.id for i in listed] == [item.id]

            # Confirm it (as the dashboard/AI would).
            await diet_plan.update_item(session, item, status="confirmed")
            assert item.status == DietItemStatus.CONFIRMED

            # Serialization shape used by the API/tool.
            d = diet_plan.item_to_dict(item)
            assert d["scheduled_date"] == "2026-07-10"
            assert d["scheduled_time"] == "14:00"
            assert d["status"] == "confirmed"
            assert d["calories"] == 600.0

            await diet_plan.delete_item(session, item)
            assert await diet_plan.list_items(session, user) == []
        finally:
            await session.rollback()


@pytest.mark.asyncio
async def test_add_item_resolves_weekday_to_date():
    async with async_session_factory() as session:
        try:
            user = User(telegram_id=920005, role=UserRole.CLIENT)
            session.add(user)
            await session.flush()

            item = await diet_plan.add_item(session, user, title="Cena", weekday=4)
            assert item.scheduled_date is not None
            assert item.scheduled_date.weekday() == 4
            assert item.scheduled_date >= date.today()
        finally:
            await session.rollback()


@pytest.mark.asyncio
async def test_get_item_scoped_to_owner():
    async with async_session_factory() as session:
        try:
            owner = User(telegram_id=920003, role=UserRole.CLIENT)
            other = User(telegram_id=920004, role=UserRole.CLIENT)
            session.add_all([owner, other])
            await session.flush()

            item = await diet_plan.add_item(session, owner, title="Ensalada")
            # The other user must not be able to fetch it.
            assert await diet_plan.get_item(session, other, item.id) is None
            assert await diet_plan.get_item(session, owner, item.id) is not None
        finally:
            await session.rollback()
