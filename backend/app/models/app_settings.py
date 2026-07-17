"""Singleton table for global settings the admin can toggle at runtime."""

from sqlalchemy import Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin

# Fixed id of the single row this table ever holds.
SETTINGS_ROW_ID = 1


class AppSettings(Base, TimestampMixin):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Nudge users over Telegram when they haven't chatted in N days.
    inactivity_reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    inactivity_reminder_days: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False
    )
