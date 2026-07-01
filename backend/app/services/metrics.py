"""Usage/cost metrics derived from stored message token counts."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.conversation import Message

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
