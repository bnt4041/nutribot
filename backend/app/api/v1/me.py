"""Authenticated client dashboard endpoints (self-service, JWT-protected)."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.models.enums import DietItemStatus
from app.models.nutrition_profile import NutritionProfile
from app.models.user import User
from app.models.weight_log import WeightLog
from app.schemas.me import (
    ConversationOut,
    DietPlanItemCreate,
    DietPlanItemOut,
    DietPlanItemUpdate,
    MessageOut,
    NoteCreate,
    NoteOut,
    ProfileOut,
    ProfileUpdateIn,
    WeightPointOut,
)
from app.services import preferences, profile as profile_service
from app.services.nutrition import diet_plan, tracking

router = APIRouter(prefix="/me", tags=["me"])


def _num(value):
    return float(value) if value is not None else None


def _profile_out(user: User, p: NutritionProfile | None) -> ProfileOut:
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


@router.get("", response_model=ProfileOut)
async def get_me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProfileOut:
    """Return the current user's account and nutrition profile."""
    p = await profile_service.get_profile(db, user)
    return _profile_out(user, p)


@router.patch("", response_model=ProfileOut)
async def update_me(
    payload: ProfileUpdateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    """Update the current user's data and objectives (partial)."""
    try:
        p = await profile_service.update_profile(
            db, user, **payload.model_dump(exclude_unset=True)
        )
    except profile_service.ProfileValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    await db.commit()
    return _profile_out(user, p)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    """Permanently delete the current user's account and all their data."""
    await profile_service.delete_account(db, user)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


# --- Recommended diet plan -------------------------------------------------


@router.get("/diet-plan", response_model=list[DietPlanItemOut])
async def my_diet_plan(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[DietPlanItemOut]:
    """The current user's recommended meals/agenda (proposed and confirmed)."""
    items = await diet_plan.list_items(db, user)
    return [DietPlanItemOut(**diet_plan.item_to_dict(i)) for i in items]


@router.post("/diet-plan", response_model=DietPlanItemOut, status_code=status.HTTP_201_CREATED)
async def create_diet_plan_item(
    payload: DietPlanItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DietPlanItemOut:
    """Add a meal to the plan. User-created items are confirmed by default."""
    data = payload.model_dump(exclude_unset=True)
    raw_status = data.pop("status", None)
    item = await diet_plan.add_item(
        db,
        user,
        source="user",
        status=DietItemStatus(raw_status) if raw_status else DietItemStatus.CONFIRMED,
        **data,
    )
    await db.commit()
    return DietPlanItemOut(**diet_plan.item_to_dict(item))


@router.patch("/diet-plan/{item_id}", response_model=DietPlanItemOut)
async def update_diet_plan_item(
    item_id: int,
    payload: DietPlanItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DietPlanItemOut:
    """Edit a plan item or confirm a proposal (status='confirmed')."""
    item = await diet_plan.get_item(db, user, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    item = await diet_plan.update_item(db, item, **payload.model_dump(exclude_unset=True))
    await db.commit()
    return DietPlanItemOut(**diet_plan.item_to_dict(item))


@router.delete("/diet-plan/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_diet_plan_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    item = await diet_plan.get_item(db, user, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await diet_plan.delete_item(db, item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- "A tener en cuenta" notes ---------------------------------------------


@router.get("/notes", response_model=list[NoteOut])
async def my_notes(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[NoteOut]:
    """Things the assistant should keep in mind about the current user."""
    notes = await preferences.list_notes(db, user)
    return [NoteOut(**preferences.note_to_dict(n)) for n in notes]


@router.post("/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteOut:
    note = await preferences.add_note(
        db, user, content=payload.content, category=payload.category, source="user"
    )
    await db.commit()
    return NoteOut(**preferences.note_to_dict(note))


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    note = await preferences.get_note(db, user, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await preferences.delete_note(db, note)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
