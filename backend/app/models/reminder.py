"""Recurring reminders/alerts sent to the user over Telegram.

Unlike the diet plan (concrete calendar dates), reminders repeat: daily or on
a fixed set of weekdays, at a given local time. A cron job (`scripts/
send_reminders.py`) scans this table every minute and pushes a Telegram
message when one is due.
"""

from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Boolean, Date, Enum, ForeignKey, Integer, String, Time
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ReminderType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    type: Mapped[ReminderType] = mapped_column(
        Enum(ReminderType, name="reminder_type"), nullable=False
    )
    # Custom text to send; required for CUSTOM, optional override for the rest
    # (falls back to a default message per type when null).
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Local time of day (interpreted against the user's profile timezone).
    time: Mapped[time] = mapped_column(Time, nullable=False)
    # 0=Monday … 6=Sunday; empty means every day.
    days_of_week: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), default=list, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Who created it: "ai" or "user".
    source: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    # Last local date it fired on; prevents re-sending within the same day.
    last_sent_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    user: Mapped["User"] = relationship(back_populates="reminders")
