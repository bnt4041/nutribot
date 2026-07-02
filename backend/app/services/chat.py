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
from app.services.deepseek.tools import FOOD_TOOLS, make_food_tool_executor
from app.services.nutrition import diet_plan
from app.services import preferences
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


async def handle_message(
    db: AsyncSession,
    telegram_id: int,
    text: str,
    full_name: str | None = None,
    start_new: bool = False,
) -> tuple[int, str]:
    """Full turn: persist user message, call DeepSeek, persist reply.

    Returns (conversation_id, assistant_reply).
    """
    user = await get_or_create_user(db, telegram_id, full_name)
    conversation = await get_or_create_conversation(db, user, start_new)

    # Persist the incoming user message first so it is part of the history.
    db.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=text,
        )
    )
    await db.flush()

    profile_result = await db.execute(
        select(NutritionProfile).where(NutritionProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()
    notes = await preferences.list_notes(db, user)
    diet_items = await diet_plan.list_items(db, user)

    # RAG: retrieve relevant knowledge for this message and inject it as context.
    system_prompt = build_system_prompt(profile, notes, diet_items)
    try:
        chunks = await retrieve(db, text)
        context_block = build_context_block(chunks)
        if context_block:
            system_prompt += context_block
    except Exception:  # noqa: BLE001 - retrieval must never break the chat
        logger.exception("RAG retrieval failed; continuing without context")

    history = await _load_history(db, conversation.id)
    messages = [
        {"role": "system", "content": system_prompt},
        *history,
    ]

    tool_executor = make_food_tool_executor(db, user)
    result: ChatResult = await deepseek_client.chat_with_tools(
        messages, FOOD_TOOLS, tool_executor
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


FOOD_PHOTO_PROMPT = """Eres NutriBot, un asistente nutricional. Analiza esta foto de comida o bebida.

Responde en español, en este formato exacto (sin Markdown, como texto de chat):

📸 He visto:
- [Nombre del plato/alimento principal]
- Ingredientes que distingas: [lista breve]
- Cantidad estimada: [aprox en gramos o unidades]
- Calorías estimadas totales: [X] kcal
- Proteína: [X]g · Carbs: [X]g · Grasa: [X]g

Después, en un párrafo aparte, di si quieres que lo registre en tu diario. Si el usuario añadió un comentario con la foto (caption), tenlo en cuenta.

Sé honesto si no puedes identificar bien algo — di "No estoy seguro" en ese caso. No inventes cifras demasiado precisas, usa rangos o aproximaciones."""


async def handle_food_photo(
    db: AsyncSession,
    user: User,
    image_base64: str,
    image_mime: str,
    caption: str | None = None,
) -> tuple[int, str]:
    """Analyze a food photo with vision AI and return the analysis.

    Does NOT auto-log — the AI response invites the user to confirm.
    Returns (conversation_id, assistant_reply).
    """
    conversation = Conversation(user_id=user.id)
    db.add(conversation)
    await db.flush()

    # Build user message with image
    user_text = caption or "¿Qué comida hay en esta foto? Analízala."
    db.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=f"📸 [Foto de comida]{' — ' + caption if caption else ''}",
        )
    )
    await db.flush()

    # Call vision model
    from app.services.deepseek.client import deepseek_client as ds_client
    from app.services.deepseek.format import sanitize_for_telegram

    messages = [
        {"role": "system", "content": FOOD_PHOTO_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image_mime};base64,{image_base64}",
                    },
                },
            ],
        },
    ]

    try:
        result = await ds_client.chat_raw(messages)
        reply = sanitize_for_telegram(result.content)
    except Exception as exc:
        logger.exception("Food photo analysis failed")
        reply = (
            "📸 No he podido analizar la foto en este momento. "
            "Puedes describirme la comida y te ayudo igualmente."
        )
        result = None

    db.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=reply,
            tokens_prompt=result.tokens_prompt if result else 0,
            tokens_completion=result.tokens_completion if result else 0,
        )
    )
    await db.commit()

    return conversation.id, reply
