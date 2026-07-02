"""
One-off migration: convert all existing MealLog records into confirmed
DietPlanItems so they appear in the Diet section of the dashboard.
"""
import asyncio
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.models.diet_plan import DietPlanItem
from app.models.enums import DietItemStatus
from app.models.meal_log import MealLog
from app.db.session import get_db  # noqa: E402

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://nutribot:nutribot@localhost:5432/nutribot",
)


async def migrate_meals_to_diet_plan():
    engine = create_async_engine(DATABASE_URL)

    async with AsyncSession(engine) as db:
        # Get all MealLogs
        result = await db.execute(select(MealLog).order_by(MealLog.id))
        meals = result.scalars().all()
        print(f"Found {len(meals)} meal logs")

        created = 0
        skipped = 0

        for meal in meals:
            # Check if a DietPlanItem already exists for this meal (same day, same title, same user)
            existing = await db.execute(
                select(DietPlanItem).where(
                    DietPlanItem.user_id == meal.user_id,
                    DietPlanItem.title == meal.food_name,
                    DietPlanItem.scheduled_date == meal.logged_at.date(),
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            item = DietPlanItem(
                user_id=meal.user_id,
                title=meal.food_name,
                scheduled_date=meal.logged_at.date(),
                meal_type=meal.meal_type,
                description=f"Registrado desde el chat — {meal.food_name}",
                calories=meal.calories,
                protein_g=meal.protein_g,
                carbs_g=meal.carbs_g,
                fat_g=meal.fat_g,
                status=DietItemStatus.CONFIRMED,
                source="ai",
            )
            db.add(item)
            created += 1

        await db.commit()
        print(f"Created {created} DietPlanItems, skipped {skipped} (already existed)")
        print("Done!")


if __name__ == "__main__":
    asyncio.run(migrate_meals_to_diet_plan())
