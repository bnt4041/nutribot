"""Authenticated client dashboard endpoints (self-service, JWT-protected)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.models.nutrition_profile import NutritionProfile
from app.models.user import User
from app.models.weight_log import WeightLog
from app.schemas.me import (
    ConversationOut,
    MessageOut,
    ProfileOut,
    WeightPointOut,
)
from app.services.nutrition import tracking

router = APIRouter(prefix="/me", tags=["me"])


def _num(value):
    return float(value) if value is not None else None


@router.get("", response_model=ProfileOut)
async def get_me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProfileOut:
    """Return the current user's account and nutrition profile."""
    result = await db.execute(
        select(NutritionProfile).where(NutritionProfile.user_id == user.id)
    )
    p = result.scalar_one_or_none()
    return ProfileOut(
        full_name=user.full_name,
        email=user.email,
        telegram_id=user.telegram_id,
        onboarding_completed=user.onboarding_completed_at is not None,
        sex=p.sex.value if p and p.sex else None,
        birth_date=p.birth_date if p else None,
        height_cm=_num(p.height_cm) if p else None,
        current_weight_kg=_num(p.current_weight_kg) if p else None,
        target_weight_kg=_num(p.target_weight_kg) if p else None,
        weekly_rate_kg=_num(p.weekly_rate_kg) if p else None,
        activity_level=p.activity_level.value if p and p.activity_level else None,
        goal=p.goal.value if p and p.goal else None,
        timezone=p.timezone if p else None,
        dietary_restrictions=p.dietary_restrictions if p else [],
        allergies=p.allergies if p else [],
        target_calories=p.target_calories if p else None,
        target_protein_g=_num(p.target_protein_g) if p else None,
        target_carbs_g=_num(p.target_carbs_g) if p else None,
        target_fat_g=_num(p.target_fat_g) if p else None,
    )


@router.get("/nutrition/summary")
async def my_summary(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Today's nutrition summary for the current user."""
    return await tracking.daily_summary(db, user)


@router.get("/nutrition/history")
async def my_history(
    days: int = Query(default=14, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Per-day macro totals for the last N days (for charts)."""
    return await tracking.history(db, user, days)


@router.get("/weight", response_model=list[WeightPointOut])
async def my_weight(
    days: int = Query(default=180, ge=1, le=730),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WeightLog]:
    """Weight history for the current user."""
    result = await db.execute(
        select(WeightLog)
        .where(WeightLog.user_id == user.id)
        .order_by(WeightLog.logged_at)
    )
    return list(result.scalars().all())


@router.get("/conversations", response_model=list[ConversationOut])
async def my_conversations(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ConversationOut]:
    """List the current user's conversations with message counts."""
    result = await db.execute(
        select(
            Conversation.id,
            Conversation.title,
            Conversation.created_at,
            func.count(Message.id).label("message_count"),
        )
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user.id)
        .group_by(Conversation.id)
        .order_by(Conversation.id.desc())
    )
    return [
        ConversationOut(
            id=row.id,
            title=row.title,
            created_at=row.created_at,
            message_count=row.message_count,
        )
        for row in result.all()
    ]


@router.get(
    "/conversations/{conversation_id}/messages", response_model=list[MessageOut]
)
async def my_conversation_messages(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Message]:
    """Messages of one of the current user's conversations."""
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    )
    return list(result.scalars().all())
