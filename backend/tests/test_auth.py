"""Tests for JWT tokens and login-code redemption."""

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.db.session import async_session_factory
from app.models.enums import UserRole
from app.models.user import User
from app.services.auth import create_login_code, issue_tokens, redeem_code


def test_access_token_round_trip():
    token = create_access_token(42, "client")
    payload = decode_token(token, "access")
    assert payload["sub"] == "42"
    assert payload["role"] == "client"
    assert payload["type"] == "access"


def test_wrong_token_type_is_rejected():
    refresh = create_refresh_token(1, "client")
    with pytest.raises(Exception):
        decode_token(refresh, "access")


def test_invalid_token_is_rejected():
    with pytest.raises(Exception):
        decode_token("not.a.token", "access")


@pytest.mark.asyncio
async def test_redeem_code_is_single_use():
    async with async_session_factory() as session:
        try:
            user = User(telegram_id=555000111, role=UserRole.CLIENT)
            session.add(user)
            await session.flush()

            code = await create_login_code(session, user)
            redeemed = await redeem_code(session, code)
            assert redeemed is not None
            assert redeemed.id == user.id

            # Second attempt must fail (already used).
            assert await redeem_code(session, code) is None
        finally:
            await session.rollback()


def test_issue_tokens_shape():
    user = User(id=7, telegram_id=1, role=UserRole.CLIENT)
    tokens = issue_tokens(user)
    assert set(tokens) == {"access_token", "refresh_token", "token_type"}
    assert decode_token(tokens["access_token"], "access")["sub"] == "7"
