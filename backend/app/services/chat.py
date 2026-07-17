"""Conversation orchestration: persistence, RAG context, and DeepSeek call."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.conversation import Conversation, Message
from app.models.enums import MessageRole
from app.models.nutrition_profile import NutritionProfile
from app.models.user import User
from app.services.deepseek.client import ChatResult, deepseek_client
from app.services.deepseek.format import sanitize_for_telegram
from app.services.deepseek.prompts import build_system_prompt
from app.services.deepseek.tools import FOOD_TOOLS, PHOTO_TOOL, make_food_tool_executor
from app.services.nutrition import diet_plan
from app.services import preferences, reminders as reminders_service
from app.services.rag.retrieval import build_context_block, retrieve

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_or_create_user(
    db: AsyncSession, telegram_id: int, full_name: str | None
) -> User:
    """Return the user for this Telegram id, creating it on first contact."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, full_name=full_name)
        db.add(user)
        await db.flush()
    elif full_name and user.full_name != full_name:
        user.full_name = full_name
    return user


async def get_or_create_conversation(
    db: AsyncSession, user: User, start_new: bool
) -> Conversation:
    """Reuse the user's latest conversation, or start a fresh one."""
    if not start_new:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.id.desc())
            .limit(1)
        )
        conversation = result.scalar_one_or_none()
        if conversation is not None:
            return conversation

    conversation = Conversation(user_id=user.id)
    db.add(conversation)
    await db.flush()
    return conversation


async def _load_history(
    db: AsyncSession, conversation_id: int
) -> list[dict[str, str]]:
    """Load the most recent messages as OpenAI-format dicts (chronological)."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .limit(settings.chat_history_limit)
    )
    recent = list(result.scalars().all())
    recent.reverse()
    return [{"role": m.role.value, "content": m.content} for m in recent]


def _format_photo_context(history: list[dict[str, str]], limit: int = 6) -> str:
    """Recent turns as plain text, for Gemini's prompt (not DeepSeek's)."""
    recent = [m for m in history if m["role"] in ("user", "assistant")][-limit:]
    speaker = {"user": "Usuario", "assistant": "Asistente"}
    return "\n".join(f"{speaker[m['role']]}: {m['content']}" for m in recent)


async def handle_message(
    db: AsyncSession,
    telegram_id: int,
    text: str | None,
    full_name: str | None = None,
    start_new: bool = False,
    image_base64: str | None = None,
    image_mime: str | None = None,
) -> tuple[int, str]:
    """Full turn: persist user message, call DeepSeek, persist reply.

    If ``image_base64`` is set, DeepSeek is given an extra tool
    (``analyze_food_photo``) and forced to call it first: DeepSeek asks
    Gemini Vision to interpret the photo (with the recent conversation as
    context) and then writes the actual reply from that result — the vision
    model never talks to the user directly.

    Returns (conversation_id, assistant_reply).
    """
    user = await get_or_create_user(db, telegram_id, full_name)
    conversation = await get_or_create_conversation(db, user, start_new)

    # Persist the incoming user message first so it is part of the history.
    stored_text = f"📸 [Foto]{' — ' + text if text else ''}" if image_base64 else (text or "Hola")
    db.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=stored_text,
        )
    )
    await db.flush()

    profile_result = await db.execute(
        select(NutritionProfile).where(NutritionProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()
    notes = await preferences.list_notes(db, user)
    diet_items = await diet_plan.list_items(db, user)
    user_reminders = await reminders_service.list_reminders(db, user)

    system_prompt = build_system_prompt(profile, notes, diet_items, user_reminders)

    history = await _load_history(db, conversation.id)

    if image_base64:
        system_prompt += (
            "\n\nEl usuario acaba de enviar una foto. Llama primero a "
            "analyze_food_photo para interpretarla antes de responder; no "
            "asumas su contenido sin comprobarlo."
        )
        tools = [*FOOD_TOOLS, PHOTO_TOOL]
        tool_executor = make_food_tool_executor(
            db,
            user,
            image_base64=image_base64,
            image_mime=image_mime,
            # Context for Gemini's prompt: what was said before this photo,
            # excluding the placeholder message just persisted above.
            conversation_context=_format_photo_context(history[:-1]),
        )
        initial_tool_choice: str | dict = {
            "type": "function",
            "function": {"name": "analyze_food_photo"},
        }
    else:
        # RAG: retrieve relevant knowledge for this message and inject it as context.
        try:
            chunks = await retrieve(db, text or "")
            context_block = build_context_block(chunks)
            if context_block:
                system_prompt += context_block
        except Exception:  # noqa: BLE001 - retrieval must never break the chat
            logger.exception("RAG retrieval failed; continuing without context")
        tools = FOOD_TOOLS
        tool_executor = make_food_tool_executor(db, user)
        initial_tool_choice = "auto"

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
    ]

    result: ChatResult = await deepseek_client.chat_with_tools(
        messages, tools, tool_executor, initial_tool_choice=initial_tool_choice
    )
    reply = sanitize_for_telegram(result.content)

    db.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=reply,
            tokens_prompt=result.tokens_prompt,
            tokens_completion=result.tokens_completion,
        )
    )
    await db.commit()

    return conversation.id, reply
