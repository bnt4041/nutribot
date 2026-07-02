"""Schemas for the unified bot interaction endpoint."""

from pydantic import BaseModel, Field


class BotButton(BaseModel):
    """A single inline-keyboard button."""

    label: str
    value: str | None = None  # sent back as `action` when tapped (callback_data)
    url: str | None = None  # external URL button (ignores value when set)


class BotMessageRequest(BaseModel):
    """Anything the user does in Telegram: a text message, a button tap, or a photo."""

    telegram_id: int
    full_name: str | None = None
    text: str | None = Field(default=None, description="Free-text message or photo caption")
    action: str | None = Field(default=None, description="Button callback value")
    image_base64: str | None = Field(
        default=None,
        description="Base64-encoded JPEG/PNG image when user sends a photo",
    )
    # MIME type of the image (e.g. image/jpeg). Helps the vision model.
    image_mime: str | None = Field(default=None)


class BotReply(BaseModel):
    """What the bot should render back to the user."""

    text: str
    buttons: list[BotButton] = Field(default_factory=list)
    # When False, the bot hides/ignores free text and expects a button tap.
    allow_free_text: bool = True
