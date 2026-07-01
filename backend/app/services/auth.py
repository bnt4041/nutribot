"""Authentication service: Telegram login codes -> JWT tokens."""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token
from app.models.login_code import LoginCode
from app.models.user import User

settings = get_settings()


def _generate_code() -> str:
    """Six-digit numeric code."""
    return f"{secrets.randbelow(1_000_000):06d}"


async def create_login_code(db: AsyncSession, user: User) -> str:
    """Create and persist a fresh login code for the user."""
    code = _generate_code()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.login_code_minutes)
    db.add(LoginCode(user_id=user.id, code=code, expires_at=expires))
    await db.flush()
    return code


async def redeem_code(db: AsyncSession, code: str) -> User | None:
    """Validate a login code and mark it used. Returns the user or None."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(LoginCode)
        .where(
            LoginCode.code == code.strip(),
            LoginCode.used_at.is_(None),
            LoginCode.expires_at > now,
        )
        .order_by(LoginCode.id.desc())
        .limit(1)
    )
    login_code = result.scalar_one_or_none()
    if login_code is None:
        return None
    login_code.used_at = now
    user = await db.get(User, login_code.user_id)
    await db.flush()
    return user


def issue_tokens(user: User) -> dict:
    """Build the access + refresh token pair for a user."""
    role = user.role.value
    return {
        "access_token": create_access_token(user.id, role),
        "refresh_token": create_refresh_token(user.id, role),
        "token_type": "bearer",
    }
