"""Recommended diet plan: scheduled meals proposed by the AI or the user."""

from datetime import date, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, Enum, ForeignKey, Numeric, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DietItemStatus, MealType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class DietPlanItem(Base, TimestampMixin):
    """A single meal in the user's recommended agenda, on a concrete date.

    ``scheduled_date`` is the calendar day the meal is planned for (or NULL for
    an unscheduled/general meal). When the user mentions a weekday, the nearest
    upcoming date is used; planning horizon is capped at ~1 month. Items start
    as ``PROPOSED`` (suggested by the assistant) and become ``CONFIRMED`` once
    the user accepts them by chat or in the dashboard.
    """

    __tablename__ = "diet_plan_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    meal_type: Mapped[MealType | None] = mapped_column(
        Enum(MealType, name="meal_type"), nullable=True
    )
    scheduled_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    calories: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    protein_g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    fat_g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    status: Mapped[DietItemStatus] = mapped_column(
        Enum(DietItemStatus, name="diet_item_status"),
        default=DietItemStatus.PROPOSED,
        nullable=False,
    )
    # Who created the item: "ai" or "user".
    source: Mapped[str] = mapped_column(String(16), default="ai", nullable=False)

    user: Mapped["User"] = relationship(back_populates="diet_plan_items")
