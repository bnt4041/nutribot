"""Usage/cost metrics derived from stored message token counts."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.conversation import Conversation, Message
from app.models.enums import MessageRole

settings = get_settings()


def _cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Estimated USD cost from DeepSeek per-Mtoken prices."""
    cost = (
        prompt_tokens / 1_000_000 * settings.deepseek_price_input_per_mtok
        + completion_tokens / 1_000_000 * settings.deepseek_price_output_per_mtok
    )
    return round(cost, 4)


async def usage(db: AsyncSession, days: int = 30) -> dict:
    """Aggregate token usage and estimated cost over the last ``days`` days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Overall totals.
    totals_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(Message.tokens_prompt), 0),
                func.coalesce(func.sum(Message.tokens_completion), 0),
                func.count(Message.id).filter(Message.tokens_completion.isnot(None)),
            ).where(Message.created_at >= since)
        )
    ).one()
    prompt_total, completion_total, assistant_messages = (
        int(totals_row[0]),
        int(totals_row[1]),
        int(totals_row[2]),
    )

    # Per-day series (UTC).
    day = func.date(Message.created_at)
    rows = (
        await db.execute(
            select(
                day.label("day"),
                func.coalesce(func.sum(Message.tokens_prompt), 0),
                func.coalesce(func.sum(Message.tokens_completion), 0),
            )
            .where(Message.created_at >= since)
            .group_by(day)
            .order_by(day)
        )
    ).all()
    series = [
        {
            "date": str(r[0]),
            "tokens_prompt": int(r[1]),
            "tokens_completion": int(r[2]),
            "cost_usd": _cost(int(r[1]), int(r[2])),
        }
        for r in rows
    ]

    return {
        "days": days,
        "tokens_prompt": prompt_total,
        "tokens_completion": completion_total,
        "tokens_total": prompt_total + completion_total,
        "assistant_messages": assistant_messages,
        "estimated_cost_usd": _cost(prompt_total, completion_total),
        "prices_per_mtok": {
            "input": settings.deepseek_price_input_per_mtok,
            "output": settings.deepseek_price_output_per_mtok,
        },
        "series": series,
    }


async def per_user_summary(db: AsyncSession) -> dict[int, dict]:
    """Per-user token consumption and last time they wrote to the bot.

    Used by the admin users table (personal token usage) and by the
    inactivity nudge (last_message_at) to find users who've gone quiet.
    """
    rows = (
        await db.execute(
            select(
                Conversation.user_id,
                func.max(Message.created_at).filter(Message.role == MessageRole.USER),
                func.coalesce(func.sum(Message.tokens_prompt), 0),
                func.coalesce(func.sum(Message.tokens_completion), 0),
            )
            .select_from(Conversation)
            .join(Message, Message.conversation_id == Conversation.id)
            .group_by(Conversation.user_id)
        )
    ).all()
    return {
        row[0]: {
            "last_message_at": row[1],
            "tokens_total": int(row[2]) + int(row[3]),
            "estimated_cost_usd": _cost(int(row[2]), int(row[3])),
        }
        for row in rows
    }
