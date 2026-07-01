"""Pydantic schemas for the chat endpoint."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat turn from the Telegram bot."""

    telegram_id: int = Field(..., description="Telegram user id")
    text: str = Field(..., min_length=1, description="User message text")
    full_name: str | None = Field(
        default=None, description="Telegram display name, used on first contact"
    )
    start_new: bool = Field(
        default=False, description="Start a new conversation instead of continuing"
    )


class ChatResponse(BaseModel):
    """Assistant reply for a chat turn."""

    conversation_id: int
    reply: str
