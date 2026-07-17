"""Local cache of Open Food Facts products."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FoodCache(Base):
    __tablename__ = "food_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    barcode: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    product_name: Mapped[str] = mapped_column(String(512), nullable=False)

    # Normalized macros per 100 g.
    calories_100g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    protein_100g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    carbs_100g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    fat_100g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    fiber_100g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    # Raw Open Food Facts payload for anything we didn't normalize.
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_food_cache_product_name", "product_name"),)
