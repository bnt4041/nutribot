"""User account model."""

from typing import TYPE_CHECKING

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.diet_plan import DietPlanItem
    from app.models.legal import UserConsent
    from app.models.meal_log import MealLog
    from app.models.nutrition_profile import NutritionProfile
    from app.models.reminder import Reminder
    from app.models.user_note import UserNote
    from app.models.water_log import WaterLog
    from app.models.weight_log import WeightLog


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Telegram user id (fits in BIGINT). Nullable for admins who never use the bot.
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, index=True, nullable=True
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(
        String(320), unique=True, index=True, nullable=True
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.CLIENT, nullable=False
    )
    # Only set for dashboard accounts with a password (e.g. admins). Clients log
    # in via one-time Telegram codes (Phase 7), so this stays null for them.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Key of the next onboarding step to answer; null before it starts.
    onboarding_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Set once the user finishes the onboarding questionnaire.
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Last time we sent an inactivity nudge/farewell; prevents resending it
    # every cron tick while the user stays inactive (only fires again once
    # they've chatted and gone silent again, which resets the counter below).
    last_inactivity_nudge_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # How many inactivity messages sent this silent streak: 1-3 are nudges
    # (one per `inactivity_reminder_days` multiple), 4 is the one-time
    # farewell after which we stop messaging until the user chats again.
    inactivity_nudge_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    profile: Mapped["NutritionProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    meal_logs: Mapped[list["MealLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    weight_logs: Mapped[list["WeightLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    water_logs: Mapped[list["WaterLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    diet_plan_items: Mapped[list["DietPlanItem"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notes: Mapped[list["UserNote"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    consents: Mapped[list["UserConsent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
