"""Chat endpoint: bridges the Telegram bot and DeepSeek."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import handle_message

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    """Process one conversational turn and return the assistant reply."""
    try:
        conversation_id, reply = await handle_message(
            db,
            telegram_id=payload.telegram_id,
            text=payload.text,
            full_name=payload.full_name,
            start_new=payload.start_new,
        )
    except Exception as exc:  # noqa: BLE001 - surface upstream failures as 502
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"chat processing failed: {exc}",
        ) from exc

    return ChatResponse(conversation_id=conversation_id, reply=reply)
