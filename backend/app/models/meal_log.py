"""Logged meals with computed macros."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MealType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class MealLog(Base, TimestampMixin):
    __tablename__ = "meal_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Optional link to a cached OFF product; free-text name always kept as fallback.
    food_id: Mapped[int | None] = mapped_column(
        ForeignKey("food_cache.id", ondelete="SET NULL"), nullable=True
    )
    food_name: Mapped[str] = mapped_column(String(512), nullable=False)

    quantity_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    meal_type: Mapped[MealType | None] = mapped_column(
        Enum(MealType, name="meal_type"), nullable=True
    )

    # Macros computed for the logged quantity.
    calories: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    protein_g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    fat_g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    fiber_g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user: Mapped["User"] = relationship(back_populates="meal_logs")
