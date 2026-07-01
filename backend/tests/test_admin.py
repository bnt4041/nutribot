"""Tests for password hashing and usage metrics aggregation."""

import pytest

from app.core.security import hash_password, verify_password
from app.db.session import async_session_factory
from app.models.conversation import Conversation, Message
from app.models.enums import MessageRole, UserRole
from app.models.user import User
from app.services import metrics


def test_password_hash_round_trip():
    h = hash_password("s3cret-pass")
    assert h != "s3cret-pass"
    assert verify_password("s3cret-pass", h)
    assert not verify_password("wrong", h)


def test_verify_password_handles_garbage_hash():
    assert not verify_password("x", "not-a-bcrypt-hash")


@pytest.mark.asyncio
async def test_usage_metrics_sum_tokens_and_cost():
    async with async_session_factory() as session:
        try:
            user = User(telegram_id=777001, role=UserRole.CLIENT)
            session.add(user)
            await session.flush()
            conv = Conversation(user_id=user.id)
            session.add(conv)
            await session.flush()
            session.add_all(
                [
                    Message(
                        conversation_id=conv.id,
                        role=MessageRole.ASSISTANT,
                        content="a",
                        tokens_prompt=1_000_000,
                        tokens_completion=2_000_000,
                    ),
                    Message(
                        conversation_id=conv.id,
                        role=MessageRole.USER,
                        content="b",
                    ),
                ]
            )
            await session.flush()

            result = await metrics.usage(session, days=30)
            assert result["tokens_prompt"] >= 1_000_000
            assert result["tokens_completion"] >= 2_000_000
            # Cost must be positive given non-zero tokens.
            assert result["estimated_cost_usd"] > 0
            assert result["assistant_messages"] >= 1
        finally:
            await session.rollback()
