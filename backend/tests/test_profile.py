"""Tests for self-service profile updates and account deletion."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.enums import ActivityLevel, Goal, Sex, UserRole
from app.models.nutrition_profile import NutritionProfile
from app.models.user import User
from app.models.user_note import UserNote
from app.models.weight_log import WeightLog
from app.services import preferences, profile as profile_service
from app.services.nutrition import diet_plan


async def _seed_full_profile(session) -> User:
    """A user with a complete profile so targets can be computed."""
    user = User(telegram_id=910001, role=UserRole.CLIENT)
    session.add(user)
    await session.flush()
    session.add(
        NutritionProfile(
            user_id=user.id,
            sex=Sex.MALE,
            birth_date=date(1990, 1, 1),
            height_cm=Decimal("180"),
            current_weight_kg=Decimal("80"),
            activity_level=ActivityLevel.MODERATE,
            goal=Goal.MAINTAIN,
        )
    )
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_update_weight_recomputes_targets_and_logs_weight():
    async with async_session_factory() as session:
        try:
            user = await _seed_full_profile(session)

            profile = await profile_service.update_profile(
                session, user, current_weight_kg="82.5"
            )

            # Weight applied and daily targets recomputed (non-null).
            assert profile.current_weight_kg == Decimal("82.5")
            assert profile.target_calories is not None
            assert profile.target_protein_g is not None

            # A weight-history row was created for the progress chart.
            logs = (
                await session.execute(
                    select(WeightLog).where(WeightLog.user_id == user.id)
                )
            ).scalars().all()
            assert any(w.weight_kg == Decimal("82.5") for w in logs)
        finally:
            await session.rollback()


@pytest.mark.asyncio
async def test_update_goal_and_lists_are_applied():
    async with async_session_factory() as session:
        try:
            user = await _seed_full_profile(session)
            profile = await profile_service.update_profile(
                session,
                user,
                goal="lose",
                weekly_rate_kg="0.5",
                allergies=["marisco", " frutos secos "],
                dietary_restrictions=[],
            )
            assert profile.goal == Goal.LOSE
            assert profile.weekly_rate_kg == Decimal("0.5")
            assert profile.allergies == ["marisco", "frutos secos"]
            assert profile.dietary_restrictions == []
        finally:
            await session.rollback()


@pytest.mark.asyncio
async def test_update_profile_rejects_out_of_range_and_bad_enum():
    async with async_session_factory() as session:
        try:
            user = await _seed_full_profile(session)
            with pytest.raises(profile_service.ProfileValidationError):
                await profile_service.update_profile(session, user, height_cm="5")
            with pytest.raises(profile_service.ProfileValidationError):
                await profile_service.update_profile(session, user, goal="fly")
            with pytest.raises(profile_service.ProfileValidationError):
                await profile_service.update_profile(
                    session, user, timezone="Mars/Olympus"
                )
        finally:
            await session.rollback()


@pytest.mark.asyncio
async def test_delete_account_cascades_related_data():
    async with async_session_factory() as session:
        try:
            user = await _seed_full_profile(session)
            await preferences.add_note(session, user, content="no le gusta la pera")
            await diet_plan.add_item(session, user, title="Avena")
            await session.flush()
            user_id = user.id

            await profile_service.delete_account(session, user)

            assert await session.get(User, user_id) is None
            remaining_notes = (
                await session.execute(
                    select(UserNote).where(UserNote.user_id == user_id)
                )
            ).scalars().all()
            profile_left = (
                await session.execute(
                    select(NutritionProfile).where(
                        NutritionProfile.user_id == user_id
                    )
                )
            ).scalar_one_or_none()
            assert remaining_notes == []
            assert profile_left is None
        finally:
            await session.rollback()
