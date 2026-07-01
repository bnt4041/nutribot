"""Per-user nutrition profile (1:1 with User)."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ActivityLevel, Goal, Sex
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class NutritionProfile(Base, TimestampMixin):
    __tablename__ = "nutrition_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )

    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[Sex | None] = mapped_column(Enum(Sex, name="sex"), nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    current_weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    activity_level: Mapped[ActivityLevel | None] = mapped_column(
        Enum(ActivityLevel, name="activity_level"), nullable=True
    )
    goal: Mapped[Goal | None] = mapped_column(Enum(Goal, name="goal"), nullable=True)
    target_weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    # Desired weekly weight change (kg/week); null when goal is "maintain".
    weekly_rate_kg: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(64), default="Europe/Madrid", nullable=False
    )
    reminders_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Free-form tags; kept as text arrays instead of a normalized catalog.
    dietary_restrictions: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    allergies: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )

    # Cached daily targets (computed from the metrics above in Phase 6).
    target_calories: Mapped[int | None] = mapped_column(nullable=True)
    target_protein_g: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    target_carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    target_fat_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")
