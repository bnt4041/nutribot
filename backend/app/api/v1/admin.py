"""Admin dashboard endpoints (user management, RAG legal docs, metrics).

All routes require an authenticated admin.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.legal import LegalDocument
from app.models.user import User
from app.schemas.admin import (
    LegalDocCreateIn,
    LegalDocOut,
    UserAdminOut,
    UserUpdateIn,
)
from app.services import metrics

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


# --- Users ---
@router.get("/users", response_model=list[UserAdminOut])
async def list_users(db: AsyncSession = Depends(get_db)) -> list[User]:
    result = await db.execute(select(User).order_by(User.id))
    return list(result.scalars().all())


@router.get("/users/{user_id}", response_model=UserAdminOut)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return user


@router.patch("/users/{user_id}", response_model=UserAdminOut)
async def update_user(
    user_id: int, payload: UserUpdateIn, db: AsyncSession = Depends(get_db)
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        user.role = payload.role
    await db.commit()
    await db.refresh(user)
    return user


# --- Metrics ---
@router.get("/metrics/usage")
async def usage_metrics(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await metrics.usage(db, days)


# --- Legal documents ---
@router.get("/legal", response_model=list[LegalDocOut])
async def list_legal(db: AsyncSession = Depends(get_db)) -> list[LegalDocument]:
    result = await db.execute(
        select(LegalDocument).order_by(
            LegalDocument.doc_type, LegalDocument.version.desc()
        )
    )
    return list(result.scalars().all())


@router.post("/legal", response_model=LegalDocOut, status_code=status.HTTP_201_CREATED)
async def create_legal(
    payload: LegalDocCreateIn, db: AsyncSession = Depends(get_db)
) -> LegalDocument:
    """Create a new version of a legal document, optionally activating it."""
    max_version = (
        await db.execute(
            select(func.coalesce(func.max(LegalDocument.version), 0)).where(
                LegalDocument.doc_type == payload.doc_type
            )
        )
    ).scalar_one()

    if payload.activate:
        # Only one active document per type.
        await db.execute(
            update(LegalDocument)
            .where(LegalDocument.doc_type == payload.doc_type)
            .values(is_active=False)
        )

    doc = LegalDocument(
        doc_type=payload.doc_type,
        version=int(max_version) + 1,
        content=payload.content,
        is_active=payload.activate,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.patch("/legal/{doc_id}/activate", response_model=LegalDocOut)
async def activate_legal(
    doc_id: int, db: AsyncSession = Depends(get_db)
) -> LegalDocument:
    """Make a specific legal document version the active one for its type."""
    doc = await db.get(LegalDocument, doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await db.execute(
        update(LegalDocument)
        .where(LegalDocument.doc_type == doc.doc_type)
        .values(is_active=False)
    )
    doc.is_active = True
    await db.commit()
    await db.refresh(doc)
    return doc
