"""Orchestrates the bot conversation: consent -> onboarding -> chat."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.schemas.bot import BotButton, BotReply
from app.services import onboarding
from app.services.chat import get_or_create_user, handle_message
from app.services.consent import get_active_terms, has_accepted, record_consent

CONSENT_ACCEPT = "consent:accept"
CONSENT_DECLINE = "consent:decline"

WELCOME_BACK = (
    "¡Hola de nuevo! 🥗 ¿En qué te ayudo hoy? Puedes preguntarme sobre nutrición "
    "o contarme qué has comido."
)

settings = get_settings()
PROFILE_BUTTON = BotButton(
    label="📊 Ver mi perfil",
    url=f"{settings.dashboard_client_url}/login",
)


def _with_profile_button(reply: BotReply) -> BotReply:
    """Append the profile dashboard button to any reply (except consent)."""
    buttons = list(reply.buttons)
    # Don't duplicate if already present.
    if not any(b.url == PROFILE_BUTTON.url for b in buttons if b.url):
        buttons.append(PROFILE_BUTTON)
    return BotReply(text=reply.text, buttons=buttons, allow_free_text=reply.allow_free_text)


def _consent_reply(content: str, prefix: str = "") -> BotReply:
    return BotReply(
        text=prefix + content,
        buttons=[
            BotButton(label="✅ Acepto", value=CONSENT_ACCEPT),
            BotButton(label="❌ No acepto", value=CONSENT_DECLINE),
        ],
        allow_free_text=False,
    )


async def handle_update(
    db: AsyncSession,
    telegram_id: int,
    full_name: str | None,
    text: str | None,
    action: str | None,
) -> BotReply:
    """Single entry point for every Telegram interaction."""
    user = await get_or_create_user(db, telegram_id, full_name)

    # 1) Consent gate.
    terms = await get_active_terms(db)
    if terms is not None and not await has_accepted(db, user, terms):
        if action == CONSENT_ACCEPT:
            await record_consent(db, user, terms)
            reply = await onboarding.start(db, user)
            await db.commit()
            return _with_profile_button(reply)
        prefix = ""
        if action == CONSENT_DECLINE:
            prefix = (
                "Para poder usar NutriBot necesitas aceptar los términos. "
                "Revísalos y pulsa «Acepto» cuando quieras continuar.\n\n"
            )
        await db.commit()  # persist user creation
        return _consent_reply(terms.content, prefix)

    # 2) Onboarding gate.
    if user.onboarding_completed_at is None:
        if action == "start":
            reply = (
                onboarding.current_view(user)
                if user.onboarding_step
                else await onboarding.start(db, user)
            )
            await db.commit()
            return _with_profile_button(reply)

        action_value: str | None = None
        if action and action.startswith("ob:"):
            _, step_key, value = action.split(":", 2)
            if step_key != (user.onboarding_step or ""):
                # Stale button from an earlier step: just re-show the current one.
                reply = onboarding.current_view(user) or await onboarding.start(db, user)
                await db.commit()
                return _with_profile_button(reply)
            action_value = value

        if user.onboarding_step is None:
            reply = await onboarding.start(db, user)
        else:
            reply = await onboarding.process(db, user, text=text, action_value=action_value)
        await db.commit()
        return _with_profile_button(reply)

    # 3) Normal chat (onboarding done).
    if action == "start":
        return _with_profile_button(BotReply(text=WELCOME_BACK))

    start_new = action == "nueva"
    user_text = text or "Hola"
    _, answer = await handle_message(
        db,
        telegram_id=telegram_id,
        text=user_text,
        full_name=full_name,
        start_new=start_new,
    )
    prefix = "🆕 Nueva conversación iniciada.\n\n" if start_new else ""
    return _with_profile_button(BotReply(text=prefix + answer))
