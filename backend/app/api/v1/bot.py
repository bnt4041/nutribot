"""Unified bot interaction endpoint (consent, onboarding, chat)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.bot import BotMessageRequest, BotReply
from app.services.bot_flow import handle_update
from app.services.nutrition import diet_plan, tracking
from app.services import profile as profile_service
from app.services.reports import generate_report_pdf
from sqlalchemy import select

router = APIRouter(prefix="/bot", tags=["bot"])


@router.post("/message", response_model=BotReply)
async def bot_message(
    payload: BotMessageRequest, db: AsyncSession = Depends(get_db)
) -> BotReply:
    """Process any Telegram interaction and return what the bot should show."""
    try:
        return await handle_update(
            db,
            telegram_id=payload.telegram_id,
            full_name=payload.full_name,
            text=payload.text,
            action=payload.action,
            image_base64=payload.image_base64,
            image_mime=payload.image_mime,
        )
    except Exception as exc:  # noqa: BLE001 - surface upstream failures as 502
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"bot processing failed: {exc}",
        ) from exc


@router.get("/report/{telegram_id}")
async def bot_report(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate a PDF nutrition report for a Telegram user."""
    # Find user by telegram_id
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    profile = await profile_service.get_profile(db, user)
    daily = await tracking.daily_summary(db, user)
    diet_items = await diet_plan.list_items(db, user)

    # Weight history
    from app.models.weight_log import WeightLog
    weight_result = await db.execute(
        select(WeightLog)
        .where(WeightLog.user_id == user.id)
        .order_by(WeightLog.logged_at.desc())
        .limit(30)
    )
    weight_history = list(weight_result.scalars().all())
    weight_history.reverse()

    pdf_bytes = generate_report_pdf(user, profile, daily, diet_items, weight_history)

    filename = f"NutriBot-informe-{date.today().isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
