"""Recurring reminders ("avisos y recordatorios"): CRUD shared by the API and
the AI tool, plus the default messages used when a reminder fires.
"""

from datetime import datetime, time as time_cls

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ReminderType
from app.models.reminder import Reminder
from app.models.user import User

TYPE_ES = {
    ReminderType.MEAL: "Registrar comidas",
    ReminderType.WATER: "Beber agua",
    ReminderType.WEIGHT: "Pesarse",
    ReminderType.CUSTOM: "Personalizado",
    ReminderType.NEWS: "Noticias de nutrición",
}

# Sent when the reminder has no custom `message` override. NEWS is fetched
# live when it fires (see scripts/send_reminders.py); this entry is only a
# placeholder shown in listings (dashboard, AI summary) before it first fires.
DEFAULT_MESSAGES = {
    ReminderType.MEAL: "🍽️ ¿Has registrado tus comidas de hoy? Cuéntame qué has comido.",
    ReminderType.WATER: "💧 Recuerda beber agua para llegar a tu objetivo de hoy.",
    ReminderType.WEIGHT: "⚖️ Toca pesarte hoy. Dime tu peso cuando quieras.",
    ReminderType.NEWS: "📰 Una noticia de nutrición y salud.",
}

DAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


class ReminderValidationError(ValueError):
    """Raised when a reminder field is invalid; carries a user-facing message."""


def _to_type(value) -> ReminderType:
    if isinstance(value, ReminderType):
        return value
    try:
        return ReminderType(str(value).strip().lower())
    except ValueError as exc:
        allowed = ", ".join(t.value for t in ReminderType)
        raise ReminderValidationError(f"type: valor no válido (usa: {allowed}).") from exc


def _to_time(value) -> time_cls:
    if isinstance(value, time_cls):
        return value
    text = str(value).strip()
    try:
        hour_str, minute_str = text.split(":")[:2]
        return time_cls(hour=int(hour_str), minute=int(minute_str))
    except (ValueError, IndexError) as exc:
        raise ReminderValidationError("time: usa el formato HH:MM.") from exc


def _to_days_of_week(value) -> list[int]:
    if value is None:
        return []
    try:
        days = {int(d) for d in value}
    except (TypeError, ValueError) as exc:
        raise ReminderValidationError("days_of_week: usa enteros 0 (lunes) a 6 (domingo).") from exc
    if any(d < 0 or d > 6 for d in days):
        raise ReminderValidationError("days_of_week: cada día debe estar entre 0 y 6.")
    return sorted(days)


def default_message(reminder_type: ReminderType) -> str | None:
    return DEFAULT_MESSAGES.get(reminder_type)


def is_due(reminder: Reminder, local_now: datetime) -> bool:
    """Pure check used by the cron script: does this reminder fire right now?

    ``local_now`` must already be converted to the owning user's timezone.
    """
    if not reminder.enabled:
        return False
    if reminder.last_sent_on == local_now.date():
        return False
    if reminder.days_of_week and local_now.weekday() not in reminder.days_of_week:
        return False
    return local_now.hour == reminder.time.hour and local_now.minute == reminder.time.minute


async def list_reminders(db: AsyncSession, user: User) -> list[Reminder]:
    result = await db.execute(
        select(Reminder).where(Reminder.user_id == user.id).order_by(Reminder.time, Reminder.id)
    )
    return list(result.scalars().all())


async def get_reminder(db: AsyncSession, user: User, reminder_id: int) -> Reminder | None:
    reminder = await db.get(Reminder, reminder_id)
    if reminder is None or reminder.user_id != user.id:
        return None
    return reminder


async def create_reminder(
    db: AsyncSession,
    user: User,
    *,
    type,
    time,
    message: str | None = None,
    days_of_week=None,
    enabled: bool = True,
    source: str = "user",
) -> Reminder:
    reminder_type = _to_type(type)
    message = (message or "").strip() or None
    if reminder_type == ReminderType.CUSTOM and not message:
        raise ReminderValidationError("message: obligatorio para recordatorios personalizados.")

    reminder = Reminder(
        user_id=user.id,
        type=reminder_type,
        message=message,
        time=_to_time(time),
        days_of_week=_to_days_of_week(days_of_week),
        enabled=bool(enabled),
        source=source,
    )
    db.add(reminder)
    await db.flush()
    return reminder


async def update_reminder(db: AsyncSession, reminder: Reminder, **fields) -> Reminder:
    if "type" in fields and fields["type"] is not None:
        reminder.type = _to_type(fields["type"])
    if "time" in fields and fields["time"] is not None:
        reminder.time = _to_time(fields["time"])
    if "days_of_week" in fields and fields["days_of_week"] is not None:
        reminder.days_of_week = _to_days_of_week(fields["days_of_week"])
    if "message" in fields and fields["message"] is not None:
        reminder.message = str(fields["message"]).strip() or None
    if "enabled" in fields and fields["enabled"] is not None:
        reminder.enabled = bool(fields["enabled"])

    if reminder.type == ReminderType.CUSTOM and not reminder.message:
        raise ReminderValidationError("message: obligatorio para recordatorios personalizados.")

    await db.flush()
    return reminder


async def delete_reminder(db: AsyncSession, reminder: Reminder) -> None:
    await db.delete(reminder)
    await db.flush()


def reminder_to_dict(reminder: Reminder) -> dict:
    return {
        "id": reminder.id,
        "type": reminder.type.value,
        "message": reminder.message or default_message(reminder.type),
        "time": reminder.time.strftime("%H:%M"),
        "days_of_week": reminder.days_of_week,
        "enabled": reminder.enabled,
        "source": reminder.source,
    }


def reminders_summary_lines(reminders: list[Reminder]) -> list[str]:
    """Lines describing the user's active reminders for the system prompt."""
    lines = []
    for r in reminders:
        if not r.enabled:
            continue
        days = ", ".join(DAYS_ES[d] for d in r.days_of_week) if r.days_of_week else "todos los días"
        text = r.message or default_message(r.type)
        lines.append(f"- [{TYPE_ES.get(r.type, 'Otro')}] {text} — {r.time.strftime('%H:%M')} ({days})")
    return lines
