"""Command handlers (/start, /help, /nueva, /informe)."""

import logging
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from backend_client import download_report, request_login_code, send_interaction
from config import get_settings
from render import send_reply

logger = logging.getLogger(__name__)

HELP = (
    "Comandos disponibles:\n"
    "/start - Iniciar o retomar\n"
    "/nueva - Empezar una conversación nueva\n"
    "/informe - Recibir tu informe nutricional en PDF\n"
    "/login - Obtener un código para el panel web\n"
    "/help - Esta ayuda\n\n"
    "O simplemente escríbeme tu consulta sobre nutrición. "
    "¡También puedes enviarme una foto de tu comida! 📸"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kick off the flow (consent -> onboarding -> chat), driven by the backend."""
    user = update.effective_user
    reply = await send_interaction(
        telegram_id=user.id, full_name=user.full_name, action="start"
    )
    await send_reply(update.effective_chat.id, context, reply)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP)


async def nueva(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a fresh conversation (only meaningful once onboarding is done)."""
    user = update.effective_user
    reply = await send_interaction(
        telegram_id=user.id, full_name=user.full_name, action="nueva"
    )
    await send_reply(update.effective_chat.id, context, reply)


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Give the user a one-time code to log into the web dashboard."""
    user = update.effective_user
    try:
        data = await request_login_code(user.id)
    except Exception:  # noqa: BLE001
        logger.exception("login code request failed")
        await update.message.reply_text(
            "No he podido generar el código ahora. Asegúrate de haber completado el "
            "registro con /start e inténtalo de nuevo."
        )
        return
    url = get_settings().dashboard_client_url
    await update.message.reply_text(
        f"Tu código de acceso al panel es:\n\n{data['code']}\n\n"
        f"Caduca en {data['expires_in_minutes']} minutos. "
        f"Introdúcelo en {url}"
    )


async def informe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send a PDF nutrition report to the user."""
    user = update.effective_user
    chat_id = update.effective_chat.id

    msg = await update.message.reply_text("📄 Generando tu informe nutricional...")

    try:
        pdf_bytes = await download_report(user.id)
    except Exception:  # noqa: BLE001
        logger.exception("report generation failed")
        await msg.edit_text(
            "❌ No pude generar el informe ahora. Asegúrate de haber completado "
            "el registro con /start e inténtalo de nuevo."
        )
        return

    filename = f"NutriBot-informe-{date.today().isoformat()}.pdf"
    await msg.delete()
    await context.bot.send_document(
        chat_id=chat_id,
        document=pdf_bytes,
        filename=filename,
        caption="🥗 ¡Aquí tienes tu informe nutricional!",
    )
