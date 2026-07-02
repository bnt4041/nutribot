"""Self-service profile updates and account deletion.

Shared by the client dashboard (`/me` endpoints) and the conversational AI tool
so both paths validate and persist changes the same way, and keep the cached
daily targets in sync.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActivityLevel, Goal, Sex
from app.models.nutrition_profile import NutritionProfile
from app.models.user import User
from app.models.weight_log import WeightLog
from app.services.nutrition.targets import recompute_targets

# Fields whose change invalidates the cached calorie/macro targets.
_TARGET_FIELDS = {
    "sex",
    "birth_date",
    "height_cm",
    "current_weight_kg",
    "activity_level",
    "goal",
    "weekly_rate_kg",
}

# Plausible numeric ranges, mirroring onboarding validation.
_NUM_RANGES = {
    "height_cm": (Decimal("80"), Decimal("250")),
    "current_weight_kg": (Decimal("20"), Decimal("400")),
    "target_weight_kg": (Decimal("20"), Decimal("400")),
    "weekly_rate_kg": (Decimal("0.05"), Decimal("2")),
}


class ProfileValidationError(ValueError):
    """Raised when an update value is invalid; carries a user-facing message."""


async def get_profile(db: AsyncSession, user: User) -> NutritionProfile | None:
    result = await db.execute(
        select(NutritionProfile).where(NutritionProfile.user_id == user.id)
    )
    return result.scalar_one_or_none()


async def ensure_profile(db: AsyncSession, user: User) -> NutritionProfile:
    profile = await get_profile(db, user)
    if profile is not None:
        return profile
    profile = NutritionProfile(user_id=user.id)
    db.add(profile)
    await db.flush()
    return profile


def _to_decimal(field: str, value) -> Decimal:
    try:
        num = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, AttributeError) as exc:
        raise ProfileValidationError(f"{field}: no es un número válido.") from exc
    lo, hi = _NUM_RANGES[field]
    if not (lo <= num <= hi):
        raise ProfileValidationError(f"{field}: debe estar entre {lo} y {hi}.")
    return num


def _to_date(value) -> date:
    if isinstance(value, date):
        parsed = value
    else:
        parsed = None
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(str(value).strip(), fmt).date()
                break
            except ValueError:
                continue
        if parsed is None:
            raise ProfileValidationError("birth_date: usa el formato DD/MM/AAAA.")
    age = (date.today() - parsed).days / 365.25
    if not (10 <= age <= 120):
        raise ProfileValidationError("birth_date: la fecha no es plausible.")
    return parsed


def _to_enum(field: str, enum_cls, value):
    try:
        return enum_cls(str(value).strip().lower())
    except ValueError as exc:
        allowed = ", ".join(e.value for e in enum_cls)
        raise ProfileValidationError(f"{field}: valor no válido (usa: {allowed}).") from exc


async def update_profile(
    db: AsyncSession,
    user: User,
    *,
    full_name=None,
    sex=None,
    birth_date=None,
    height_cm=None,
    current_weight_kg=None,
    activity_level=None,
    goal=None,
    target_weight_kg=None,
    weekly_rate_kg=None,
    timezone=None,
    reminders_enabled=None,
    dietary_restrictions=None,
    allergies=None,
) -> NutritionProfile:
    """Apply the provided (non-None) fields to the user's profile.

    Values may be raw strings (from the AI tool) or already-typed values (from
    Pydantic); both are coerced and range-checked. Raises ProfileValidationError
    on invalid input. Recomputes daily targets when a relevant field changes.
    """
    profile = await ensure_profile(db, user)
    changed_targets = False

    if full_name is not None:
        user.full_name = str(full_name).strip() or None

    if sex is not None:
        profile.sex = _to_enum("sex", Sex, sex)
        changed_targets = True
    if birth_date is not None:
        profile.birth_date = _to_date(birth_date)
        changed_targets = True
    if height_cm is not None:
        profile.height_cm = _to_decimal("height_cm", height_cm)
        changed_targets = True
    if current_weight_kg is not None:
        new_weight = _to_decimal("current_weight_kg", current_weight_kg)
        if new_weight != profile.current_weight_kg:
            db.add(WeightLog(user_id=user.id, weight_kg=new_weight))  # keep history
        profile.current_weight_kg = new_weight
        changed_targets = True
    if activity_level is not None:
        profile.activity_level = _to_enum("activity_level", ActivityLevel, activity_level)
        changed_targets = True
    if goal is not None:
        profile.goal = _to_enum("goal", Goal, goal)
        changed_targets = True
    if target_weight_kg is not None:
        profile.target_weight_kg = _to_decimal("target_weight_kg", target_weight_kg)
    if weekly_rate_kg is not None:
        profile.weekly_rate_kg = _to_decimal("weekly_rate_kg", weekly_rate_kg)
        changed_targets = True
    if timezone is not None:
        tz = str(timezone).strip()
        try:
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ProfileValidationError("timezone: zona horaria no reconocida.") from exc
        profile.timezone = tz
    if reminders_enabled is not None:
        profile.reminders_enabled = bool(reminders_enabled)
    if dietary_restrictions is not None:
        profile.dietary_restrictions = [str(x).strip() for x in dietary_restrictions if str(x).strip()]
    if allergies is not None:
        profile.allergies = [str(x).strip() for x in allergies if str(x).strip()]

    await db.flush()
    if changed_targets:
        await recompute_targets(db, profile)
    return profile


async def delete_account(db: AsyncSession, user: User) -> None:
    """Permanently delete the user and all related data (cascade)."""
    await db.delete(user)
    await db.flush()
