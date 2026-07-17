"""Recommended diet plan: CRUD shared by the dashboard API and the AI tool.

Meals are scheduled on concrete calendar dates. When only a weekday is given
(e.g. the user says "el viernes"), the nearest upcoming date is used.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diet_plan import DietPlanItem
from app.models.enums import DietItemStatus, MealType
from app.models.user import User
from app.services.nutrition import tracking

DAYS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MEAL_ES = {
    MealType.BREAKFAST: "Desayuno",
    MealType.LUNCH: "Comida",
    MealType.DINNER: "Cena",
    MealType.SNACK: "Snack",
}
# How far ahead a meal may be planned (matches the "un mes máximo" rule).
MAX_HORIZON_DAYS = 31


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def _to_meal_type(value) -> MealType | None:
    if not value:
        return None
    try:
        return MealType(str(value).strip().lower())
    except ValueError:
        return None


def _to_time(value) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    raw = str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None


def next_weekday_date(weekday: int, from_date: date | None = None) -> date:
    """Nearest date on or after ``from_date`` whose weekday is ``weekday``.

    ``weekday`` is 0=Monday … 6=Sunday (matching ``date.weekday()``).
    """
    base = from_date or date.today()
    ahead = (weekday - base.weekday()) % 7
    return base + timedelta(days=ahead)


def resolve_date(scheduled_date=None, weekday=None) -> date | None:
    """Turn an explicit date or a weekday hint into a concrete date.

    Accepts a ``date``/ISO string in ``scheduled_date``, or a weekday index
    (0=Mon … 6=Sun) in ``weekday``, resolving the latter to the nearest
    upcoming date. Returns None when neither is usable.
    """
    if scheduled_date not in (None, ""):
        if isinstance(scheduled_date, date):
            return scheduled_date
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(str(scheduled_date).strip(), fmt).date()
            except ValueError:
                continue
        return None
    if weekday not in (None, ""):
        try:
            wd = int(weekday)
        except (TypeError, ValueError):
            return None
        if 0 <= wd <= 6:
            return next_weekday_date(wd)
    return None


async def list_items(db: AsyncSession, user: User) -> list[DietPlanItem]:
    result = await db.execute(
        select(DietPlanItem)
        .where(DietPlanItem.user_id == user.id)
        .order_by(
            DietPlanItem.scheduled_date.nulls_last(),
            DietPlanItem.scheduled_time.nulls_last(),
            DietPlanItem.id,
        )
    )
    return list(result.scalars().all())


async def add_item(
    db: AsyncSession,
    user: User,
    *,
    title: str,
    scheduled_date=None,
    weekday=None,
    meal_type=None,
    scheduled_time=None,
    description: str | None = None,
    calories=None,
    protein_g=None,
    carbs_g=None,
    fat_g=None,
    fiber_g=None,
    status: DietItemStatus = DietItemStatus.PROPOSED,
    source: str = "ai",
) -> DietPlanItem:
    item = DietPlanItem(
        user_id=user.id,
        title=title.strip(),
        scheduled_date=resolve_date(scheduled_date, weekday),
        meal_type=_to_meal_type(meal_type),
        scheduled_time=_to_time(scheduled_time),
        description=(description.strip() if description else None),
        calories=_to_decimal(calories),
        protein_g=_to_decimal(protein_g),
        carbs_g=_to_decimal(carbs_g),
        fat_g=_to_decimal(fat_g),
        fiber_g=_to_decimal(fiber_g),
        status=status,
        source=source,
    )
    db.add(item)
    await db.flush()
    if item.status == DietItemStatus.CONFIRMED:
        await tracking.log_confirmed_diet_item(db, item)
    return item


async def get_item(db: AsyncSession, user: User, item_id: int) -> DietPlanItem | None:
    item = await db.get(DietPlanItem, item_id)
    if item is None or item.user_id != user.id:
        return None
    return item


async def update_item(db: AsyncSession, item: DietPlanItem, **fields) -> DietPlanItem:
    if "title" in fields and fields["title"] is not None:
        item.title = str(fields["title"]).strip()
    if "description" in fields:
        desc = fields["description"]
        item.description = str(desc).strip() if desc else None
    # A date or a weekday hint may be supplied to reschedule the meal.
    if "scheduled_date" in fields or "weekday" in fields:
        item.scheduled_date = resolve_date(
            fields.get("scheduled_date"), fields.get("weekday")
        )
    if "meal_type" in fields:
        item.meal_type = _to_meal_type(fields["meal_type"])
    if "scheduled_time" in fields:
        item.scheduled_time = _to_time(fields["scheduled_time"])
    for macro in ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g"):
        if macro in fields:
            setattr(item, macro, _to_decimal(fields[macro]))
    was_confirmed = item.status == DietItemStatus.CONFIRMED
    if fields.get("status") is not None:
        status = fields["status"]
        item.status = status if isinstance(status, DietItemStatus) else DietItemStatus(str(status).lower())
    await db.flush()
    if item.status == DietItemStatus.CONFIRMED and not was_confirmed:
        await tracking.log_confirmed_diet_item(db, item)
    return item


async def delete_item(db: AsyncSession, item: DietPlanItem) -> None:
    await db.delete(item)
    await db.flush()


def item_to_dict(item: DietPlanItem) -> dict:
    return {
        "id": item.id,
        "scheduled_date": item.scheduled_date.isoformat() if item.scheduled_date else None,
        "meal_type": item.meal_type.value if item.meal_type else None,
        "scheduled_time": item.scheduled_time.strftime("%H:%M") if item.scheduled_time else None,
        "title": item.title,
        "description": item.description,
        "calories": float(item.calories) if item.calories is not None else None,
        "protein_g": float(item.protein_g) if item.protein_g is not None else None,
        "carbs_g": float(item.carbs_g) if item.carbs_g is not None else None,
        "fat_g": float(item.fat_g) if item.fat_g is not None else None,
        "fiber_g": float(item.fiber_g) if item.fiber_g is not None else None,
        "status": item.status.value,
        "source": item.source,
    }


def plan_summary_lines(items: list[DietPlanItem]) -> list[str]:
    """Compact, human-readable lines describing the plan for the system prompt."""
    lines: list[str] = []
    for item in items:
        parts: list[str] = []
        if item.scheduled_date is not None:
            parts.append(
                f"{DAYS_ES[item.scheduled_date.weekday()]} {item.scheduled_date.isoformat()}"
            )
        if item.meal_type is not None:
            parts.append(MEAL_ES.get(item.meal_type, item.meal_type.value))
        if item.scheduled_time is not None:
            parts.append(item.scheduled_time.strftime("%H:%M"))
        prefix = " ".join(parts)
        state = "confirmada" if item.status == DietItemStatus.CONFIRMED else "propuesta"
        head = f"{prefix}: {item.title}" if prefix else item.title
        lines.append(f"- {head} ({state})")
    return lines
