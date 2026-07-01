"""Nutrition tracking endpoints (daily summary).

Currently keyed by telegram_id for verification and for the client dashboard
(Phase 7), which will add proper auth.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.nutrition.tracking import daily_summary

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/summary/{telegram_id}")
async def get_summary(
    telegram_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    """Return today's nutrition summary for a user (by Telegram id)."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return await daily_summary(db, user)
