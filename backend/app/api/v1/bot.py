"""Unified bot interaction endpoint (consent, onboarding, chat)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.bot import BotMessageRequest, BotReply
from app.services.bot_flow import handle_update

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
