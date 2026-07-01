"""Schemas for the unified bot interaction endpoint."""

from pydantic import BaseModel, Field


class BotButton(BaseModel):
    """A single inline-keyboard button."""

    label: str
    value: str  # sent back as `action` when tapped


class BotMessageRequest(BaseModel):
    """Anything the user does in Telegram: a text message or a button tap."""

    telegram_id: int
    full_name: str | None = None
    text: str | None = Field(default=None, description="Free-text message")
    action: str | None = Field(default=None, description="Button callback value")


class BotReply(BaseModel):
    """What the bot should render back to the user."""

    text: str
    buttons: list[BotButton] = Field(default_factory=list)
    # When False, the bot hides/ignores free text and expects a button tap.
    allow_free_text: bool = True
