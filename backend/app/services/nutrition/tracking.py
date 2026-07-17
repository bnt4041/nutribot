"""Meal logging and daily macro aggregation."""

from datetime import date as date_cls
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diet_plan import DietPlanItem
from app.models.enums import DietItemStatus, MealType
from app.models.food_cache import FoodCache
from app.models.meal_log import MealLog
from app.models.nutrition_profile import NutritionProfile
from app.models.user import User
from app.models.water_log import WaterLog
from app.services.nutrition.targets import ensure_targets
from app.services.openfoodfacts import service as off_service

DEFAULT_TZ = "Europe/Madrid"


def scale_macros(per_100g: dict, grams: float) -> dict:
    """Scale per-100g macros to a given quantity in grams."""
    factor = grams / 100.0

    def _s(value):
        return round(value * factor, 1) if value is not None else None

    return {
        "calories": _s(per_100g.get("calories_100g")),
        "protein_g": _s(per_100g.get("protein_100g")),
        "carbs_g": _s(per_100g.get("carbs_100g")),
        "fat_g": _s(per_100g.get("fat_100g")),
        "fiber_g": _s(per_100g.get("fiber_100g")),
    }


def _parse_meal_type(value: str | None) -> MealType | None:
    if not value:
        return None
    try:
        return MealType(value.lower())
    except ValueError:
        return None


async def _profile(db: AsyncSession, user: User) -> NutritionProfile | None:
    result = await db.execute(
        select(NutritionProfile).where(NutritionProfile.user_id == user.id)
    )
    return result.scalar_one_or_none()


async def log_meal(
    db: AsyncSession,
    user: User,
    food_name: str,
    quantity_g: float | None = None,
    meal_type: str | None = None,
    barcode: str | None = None,
    calories: float | None = None,
    protein_g: float | None = None,
    carbs_g: float | None = None,
    fat_g: float | None = None,
    fiber_g: float | None = None,
) -> dict:
    """Record a meal and return a confirmation plus today's running summary.

    Macro source priority: a barcode (exact OFF data scaled by quantity) wins;
    otherwise the caller-provided macro totals are stored as-is.
    """
    food_id: int | None = None
    macros = {
        "calories": calories,
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g,
        "fiber_g": fiber_g,
    }

    if barcode:
        product = await off_service.get_by_barcode(db, barcode)
        if product is not None:
            food_name = food_name or product["name"]
            row = await db.execute(
                select(FoodCache).where(FoodCache.barcode == barcode)
            )
            cached = row.scalar_one_or_none()
            food_id = cached.id if cached else None
            if quantity_g:
                macros = scale_macros(product, quantity_g)

    if macros["calories"] is None and macros["protein_g"] is None:
        return {
            "logged": False,
            "message": (
                "Necesito los macros o un código de barras para registrar la comida."
            ),
        }

    meal = MealLog(
        user_id=user.id,
        food_id=food_id,
        food_name=food_name,
        quantity_g=quantity_g if quantity_g is not None else 0,
        meal_type=_parse_meal_type(meal_type),
        calories=macros["calories"],
        protein_g=macros["protein_g"],
        carbs_g=macros["carbs_g"],
        fat_g=macros["fat_g"],
        fiber_g=macros["fiber_g"],
    )
    db.add(meal)
    await db.flush()

    # Also create a confirmed DietPlanItem so the meal appears in the Diet section.
    today = date_cls.today()
    diet_item = DietPlanItem(
        user_id=user.id,
        title=food_name,
        scheduled_date=today,
        meal_type=_parse_meal_type(meal_type),
        description=f"Registrado desde el chat — {food_name}",
        calories=macros["calories"],
        protein_g=macros["protein_g"],
        carbs_g=macros["carbs_g"],
        fat_g=macros["fat_g"],
        fiber_g=macros["fiber_g"],
        status=DietItemStatus.CONFIRMED,
        source="ai",
    )
    db.add(diet_item)
    await db.flush()

    summary = await daily_summary(db, user)
    return {"logged": True, "meal": _meal_to_dict(meal), "daily_summary": summary}


def _meal_to_dict(meal: MealLog) -> dict:
    return {
        "food_name": meal.food_name,
        "quantity_g": float(meal.quantity_g) if meal.quantity_g is not None else None,
        "meal_type": meal.meal_type.value if meal.meal_type else None,
        "calories": float(meal.calories) if meal.calories is not None else None,
        "protein_g": float(meal.protein_g) if meal.protein_g is not None else None,
        "carbs_g": float(meal.carbs_g) if meal.carbs_g is not None else None,
        "fat_g": float(meal.fat_g) if meal.fat_g is not None else None,
        "fiber_g": float(meal.fiber_g) if meal.fiber_g is not None else None,
    }


async def log_confirmed_diet_item(db: AsyncSession, item: DietPlanItem) -> MealLog | None:
    """Record a just-confirmed diet-plan item as a meal log entry.

    Without this, confirming a planned meal (by chat or in the dashboard) only
    flips its status and never counts toward the day's totals/charts, since
    those are computed from ``MealLog`` alone.
    """
    if item.calories is None and item.protein_g is None:
        return None

    result = await db.execute(
        select(NutritionProfile).where(NutritionProfile.user_id == item.user_id)
    )
    profile = result.scalar_one_or_none()
    tz_name = profile.timezone if profile and profile.timezone else DEFAULT_TZ
    tz = ZoneInfo(tz_name)

    day = item.scheduled_date or datetime.now(tz).date()
    logged_at = datetime.combine(day, item.scheduled_time or time(12, 0), tzinfo=tz)

    meal = MealLog(
        user_id=item.user_id,
        food_name=item.title,
        quantity_g=0,
        meal_type=item.meal_type,
        calories=item.calories,
        protein_g=item.protein_g,
        carbs_g=item.carbs_g,
        fat_g=item.fat_g,
        fiber_g=item.fiber_g,
        logged_at=logged_at,
    )
    db.add(meal)
    await db.flush()
    return meal


async def log_water(db: AsyncSession, user: User, amount_ml: float) -> dict:
    """Record water intake and return a confirmation plus today's summary."""
    if not amount_ml or amount_ml <= 0:
        return {"logged": False, "message": "La cantidad de agua debe ser mayor que 0 ml."}

    entry = WaterLog(user_id=user.id, amount_ml=amount_ml)
    db.add(entry)
    await db.flush()

    summary = await daily_summary(db, user)
    return {"logged": True, "amount_ml": float(amount_ml), "daily_summary": summary}


async def _water_total(
    db: AsyncSession, user: User, start: datetime, end: datetime
) -> float:
    result = await db.execute(
        select(WaterLog).where(
            WaterLog.user_id == user.id,
            WaterLog.logged_at >= start,
            WaterLog.logged_at < end,
        )
    )
    return sum(float(w.amount_ml) for w in result.scalars().all())


async def history(db: AsyncSession, user: User, days: int = 14) -> list[dict]:
    """Per-day macro totals for the last ``days`` days (user's timezone)."""
    profile = await _profile(db, user)
    tz_name = profile.timezone if profile and profile.timezone else DEFAULT_TZ
    tz = ZoneInfo(tz_name)

    today = datetime.now(tz).date()
    start_date = today - timedelta(days=days - 1)
    start = datetime.combine(start_date, time.min, tzinfo=tz)

    result = await db.execute(
        select(MealLog)
        .where(MealLog.user_id == user.id, MealLog.logged_at >= start)
        .order_by(MealLog.logged_at)
    )
    water_result = await db.execute(
        select(WaterLog)
        .where(WaterLog.user_id == user.id, WaterLog.logged_at >= start)
        .order_by(WaterLog.logged_at)
    )
    # Bucket meals (and water) by local date.
    buckets: dict[str, dict] = {}
    for i in range(days):
        d = (start_date + timedelta(days=i)).isoformat()
        buckets[d] = {
            "date": d,
            "calories": 0.0,
            "protein_g": 0.0,
            "carbs_g": 0.0,
            "fat_g": 0.0,
            "fiber_g": 0.0,
            "water_ml": 0.0,
        }
    for meal in result.scalars().all():
        local_date = meal.logged_at.astimezone(tz).date().isoformat()
        bucket = buckets.get(local_date)
        if bucket is None:
            continue
        bucket["calories"] += float(meal.calories or 0)
        bucket["protein_g"] += float(meal.protein_g or 0)
        bucket["carbs_g"] += float(meal.carbs_g or 0)
        bucket["fat_g"] += float(meal.fat_g or 0)
        bucket["fiber_g"] += float(meal.fiber_g or 0)
    for water in water_result.scalars().all():
        local_date = water.logged_at.astimezone(tz).date().isoformat()
        bucket = buckets.get(local_date)
        if bucket is None:
            continue
        bucket["water_ml"] += float(water.amount_ml or 0)
    return [
        {k: (round(v, 1) if isinstance(v, float) else v) for k, v in b.items()}
        for b in buckets.values()
    ]


async def daily_summary(
    db: AsyncSession, user: User, day: date_cls | None = None
) -> dict:
    """Sum a day's meals (in the user's timezone) and compare with targets."""
    profile = await _profile(db, user)
    tz_name = profile.timezone if profile and profile.timezone else DEFAULT_TZ
    tz = ZoneInfo(tz_name)

    target_day = day or datetime.now(tz).date()
    start = datetime.combine(target_day, time.min, tzinfo=tz)
    end = start + timedelta(days=1)

    result = await db.execute(
        select(MealLog)
        .where(
            MealLog.user_id == user.id,
            MealLog.logged_at >= start,
            MealLog.logged_at < end,
        )
        .order_by(MealLog.logged_at)
    )
    meals = list(result.scalars().all())
    water_total = await _water_total(db, user, start, end)

    totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0}
    for meal in meals:
        totals["calories"] += float(meal.calories or 0)
        totals["protein_g"] += float(meal.protein_g or 0)
        totals["carbs_g"] += float(meal.carbs_g or 0)
        totals["fat_g"] += float(meal.fat_g or 0)
        totals["fiber_g"] += float(meal.fiber_g or 0)
    totals = {k: round(v, 1) for k, v in totals.items()}

    targets = await ensure_targets(db, profile) if profile else None
    targets_dict = None
    remaining = None
    water_target = targets.water_ml if targets is not None else None
    if targets is not None:
        targets_dict = {
            "calories": targets.calories,
            "protein_g": targets.protein_g,
            "carbs_g": targets.carbs_g,
            "fat_g": targets.fat_g,
            "fiber_g": targets.fiber_g,
        }
        remaining = {
            "calories": round(targets.calories - totals["calories"], 1),
            "protein_g": round(targets.protein_g - totals["protein_g"], 1),
            "carbs_g": round(targets.carbs_g - totals["carbs_g"], 1),
            "fat_g": round(targets.fat_g - totals["fat_g"], 1),
            "fiber_g": round(targets.fiber_g - totals["fiber_g"], 1),
        }

    return {
        "date": target_day.isoformat(),
        "timezone": tz_name,
        "totals": totals,
        "targets": targets_dict,
        "remaining": remaining,
        "water_ml": round(water_total, 1),
        "water_target_ml": water_target,
        "water_remaining_ml": (
            round(water_target - water_total, 1) if water_target else None
        ),
        "meals": [_meal_to_dict(m) for m in meals],
    }
