"""Cron entrypoint: push due reminders to Telegram.

Invoked every minute by cron (see ../crontab). Each run is a fresh, short-lived
process: it checks every enabled reminder against "now" in the owning user's
timezone and sends the ones due this exact minute, deduping via
`last_sent_on` so re-running within the same minute (or a clock hiccup)
can't double-send the same day.

Usage (inside the backend/cron container):
    uv run python scripts/send_reminders.py
"""

import asyncio
import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.enums import ReminderType, UserRole
from app.models.reminder import Reminder
from app.models.user import User
from app.services import app_settings as app_settings_service
from app.services import metrics
from app.services import nutrition_news
from app.services.inactivity import compute_slot, message_for_slot
from app.services.reminders import default_message, is_due

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("send_reminders")

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
FALLBACK_TZ = "Europe/Madrid"


def _resolve_timezone(tz_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name or FALLBACK_TZ)
    except ZoneInfoNotFoundError:
        return ZoneInfo(FALLBACK_TZ)


async def _send_telegram_message(token: str, chat_id: int, text: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            TELEGRAM_API_URL.format(token=token),
            json={"chat_id": chat_id, "text": text},
        )
        response.raise_for_status()


async def _reminder_text(reminder: Reminder) -> str:
    """Message to send for a due reminder. NEWS fetches a live headline
    unless the user set a custom message override for it."""
    if reminder.type == ReminderType.NEWS and not reminder.message:
        try:
            headline = await nutrition_news.fetch_headline()
        except httpx.HTTPError:
            logger.exception("Failed to fetch nutrition news for reminder id=%s", reminder.id)
            headline = None
        return nutrition_news.format_message(headline)
    return reminder.message or default_message(reminder.type)


async def _check_inactivity_nudges(db: AsyncSession, token: str) -> None:
    app_settings = await app_settings_service.get_settings(db)
    if not app_settings.inactivity_reminder_enabled:
        return

    summary = await metrics.per_user_summary(db)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(User)
        .options(joinedload(User.profile))
        .where(User.role == UserRole.CLIENT, User.telegram_id.isnot(None))
    )
    for user in result.scalars().unique():
        if user.onboarding_completed_at is None:
            continue
        profile = user.profile
        if profile is None or not profile.reminders_enabled:
            continue

        last_activity = summary.get(user.id, {}).get("last_message_at") or user.created_at
        if user.last_inactivity_nudge_at and last_activity > user.last_inactivity_nudge_at:
            # Chatted again since the last nudge: the silent streak reset.
            user.inactivity_nudge_count = 0

        days_silent = (now - last_activity).total_seconds() / 86400
        slot = compute_slot(days_silent, app_settings.inactivity_reminder_days, user.inactivity_nudge_count)
        if slot is None:
            continue

        try:
            await _send_telegram_message(token, user.telegram_id, message_for_slot(slot))
        except httpx.HTTPError:
            logger.exception(
                "Failed to send inactivity nudge slot=%s to telegram_id=%s", slot, user.telegram_id
            )
            continue
        user.inactivity_nudge_count = slot
        user.last_inactivity_nudge_at = now
        logger.info(
            "Sent inactivity slot=%s to telegram_id=%s (%.1f days silent)",
            slot,
            user.telegram_id,
            days_silent,
        )


async def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is not set; skipping this run")
        return

    async with async_session_factory() as db:
        result = await db.execute(
            select(Reminder)
            .where(Reminder.enabled.is_(True))
            .options(joinedload(Reminder.user).joinedload(User.profile))
        )
        reminders = result.scalars().unique().all()

        due: list[tuple[Reminder, User, date]] = []
        for reminder in reminders:
            user = reminder.user
            if user is None or user.telegram_id is None:
                continue
            profile = user.profile
            if profile is None or not profile.reminders_enabled:
                continue
            local_now = datetime.now(_resolve_timezone(profile.timezone))
            if is_due(reminder, local_now):
                due.append((reminder, user, local_now.date()))

        for reminder, user, local_today in due:
            text = await _reminder_text(reminder)
            try:
                await _send_telegram_message(
                    settings.telegram_bot_token, user.telegram_id, text
                )
            except httpx.HTTPError:
                logger.exception(
                    "Failed to send reminder id=%s to telegram_id=%s",
                    reminder.id,
                    user.telegram_id,
                )
                continue
            reminder.last_sent_on = local_today
            logger.info(
                "Sent reminder id=%s type=%s to telegram_id=%s",
                reminder.id,
                reminder.type.value,
                user.telegram_id,
            )

        await _check_inactivity_nudges(db, settings.telegram_bot_token)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
