"""Message and button handlers: relay to the backend and render the reply."""

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from backend_client import download_report, send_interaction, send_photo_interaction
from render import send_reply

logger = logging.getLogger(__name__)

ERROR_TEXT = "Ups, ha ocurrido un error. Inténtalo de nuevo en un momento."
PHOTO_ERROR_TEXT = "📸 No pude procesar la foto. ¿Puedes describirme la comida?"


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward a free-text message to the backend."""
    user = update.effective_user
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )
    try:
        reply = await send_interaction(
            telegram_id=user.id, full_name=user.full_name, text=update.message.text
        )
    except Exception:  # noqa: BLE001 - keep the bot responsive on any failure
        logger.exception("backend interaction failed")
        await update.message.reply_text(ERROR_TEXT)
        return
    await send_reply(update.effective_chat.id, context, reply)


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download a food photo and send it to the backend for AI analysis."""
    user = update.effective_user
    chat_id = update.effective_chat.id

    # Let the user know we're working on it
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        # Get the largest photo (last in the array)
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()

        caption = update.message.caption or None

        reply = await send_photo_interaction(
            telegram_id=user.id,
            full_name=user.full_name,
            image_bytes=bytes(image_bytes),
            caption=caption,
        )
    except Exception:  # noqa: BLE001
        logger.exception("photo interaction failed")
        await context.bot.send_message(chat_id=chat_id, text=PHOTO_ERROR_TEXT)
        return
    await send_reply(chat_id, context, reply)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline-button taps (consent / onboarding choices / informe)."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    chat_id = update.effective_chat.id

    # ── "informe" action: download and send PDF directly ────────────────
    if query.data == "informe":
        await query.edit_message_text("📄 Generando tu informe nutricional...")
        try:
            pdf_bytes = await download_report(user.id)
        except Exception:
            logger.exception("report download failed")
            await query.edit_message_text(
                "❌ No pude generar el informe ahora. Usa /informe para reintentar."
            )
            return
        from datetime import date
        filename = f"NutriBot-informe-{date.today().isoformat()}.pdf"
        await context.bot.send_document(
            chat_id=chat_id,
            document=pdf_bytes,
            filename=filename,
            caption="🥗 ¡Aquí tienes tu informe nutricional!",
        )
        return

    # Remove the keyboard from the tapped message to avoid stale re-taps.
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001 - non-critical UI cleanup
        pass

    try:
        reply = await send_interaction(
            telegram_id=user.id, full_name=user.full_name, action=query.data
        )
    except Exception:  # noqa: BLE001
        logger.exception("backend interaction failed")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=ERROR_TEXT)
        return
    await send_reply(update.effective_chat.id, context, reply)
