"""Authentication endpoints: login-code request, login, token refresh."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token, decode_token, verify_password
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import (
    AccessOut,
    AdminLoginIn,
    CodeOut,
    LoginIn,
    RefreshIn,
    RequestCodeIn,
    TokenOut,
)
from app.services.auth import create_login_code, issue_tokens, redeem_code

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/request-code", response_model=CodeOut)
async def request_code(
    payload: RequestCodeIn, db: AsyncSession = Depends(get_db)
) -> CodeOut:
    """Create a login code for a Telegram user (called by the bot)."""
    result = await db.execute(
        select(User).where(User.telegram_id == payload.telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    code = await create_login_code(db, user)
    await db.commit()
    return CodeOut(code=code, expires_in_minutes=settings.login_code_minutes)


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    """Exchange a valid login code for access + refresh tokens."""
    user = await redeem_code(db, payload.code)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="código inválido o caducado"
        )
    await db.commit()
    return TokenOut(**issue_tokens(user))


@router.post("/admin/login", response_model=TokenOut)
async def admin_login(
    payload: AdminLoginIn, db: AsyncSession = Depends(get_db)
) -> TokenOut:
    """Email + password login for admin dashboard users."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if (
        user is None
        or user.role != UserRole.ADMIN
        or not user.is_active
        or not user.password_hash
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="credenciales inválidas"
        )
    return TokenOut(**issue_tokens(user))


@router.post("/refresh", response_model=AccessOut)
async def refresh(payload: RefreshIn, db: AsyncSession = Depends(get_db)) -> AccessOut:
    """Issue a new access token from a valid refresh token."""
    token_payload = decode_token(payload.refresh_token, "refresh")
    user = await db.get(User, int(token_payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found"
        )
    return AccessOut(access_token=create_access_token(user.id, user.role.value))
