"""Global admin-controlled settings (singleton row)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import SETTINGS_ROW_ID, AppSettings


async def get_settings(db: AsyncSession) -> AppSettings:
    settings = await db.get(AppSettings, SETTINGS_ROW_ID)
    if settings is not None:
        return settings
    settings = AppSettings(id=SETTINGS_ROW_ID)
    db.add(settings)
    await db.flush()
    return settings


async def update_settings(
    db: AsyncSession,
    *,
    inactivity_reminder_enabled: bool | None = None,
    inactivity_reminder_days: int | None = None,
) -> AppSettings:
    settings = await get_settings(db)
    if inactivity_reminder_enabled is not None:
        settings.inactivity_reminder_enabled = bool(inactivity_reminder_enabled)
    if inactivity_reminder_days is not None:
        settings.inactivity_reminder_days = max(1, int(inactivity_reminder_days))
    await db.flush()
    return settings
