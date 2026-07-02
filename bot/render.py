"""Helpers to render a backend BotReply into Telegram messages."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


def build_markup(buttons: list[dict] | None) -> InlineKeyboardMarkup | None:
    """Build an inline keyboard (one button per row) from BotReply buttons."""
    if not buttons:
        return None
    keyboard = []
    for b in buttons:
        if b.get("url"):
            keyboard.append([InlineKeyboardButton(b["label"], url=b["url"])])
        else:
            keyboard.append([InlineKeyboardButton(b["label"], callback_data=b.get("value", ""))])
    return InlineKeyboardMarkup(keyboard)


async def send_reply(
    chat_id: int, context: ContextTypes.DEFAULT_TYPE, reply: dict
) -> None:
    """Send a BotReply dict to the chat, with buttons if present."""
    await context.bot.send_message(
        chat_id=chat_id,
        text=reply["text"],
        reply_markup=build_markup(reply.get("buttons")),
    )
