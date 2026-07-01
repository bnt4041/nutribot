"""Schemas for admin dashboard endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import LegalDocType, UserRole


class UserAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int | None
    full_name: str | None
    email: str | None
    role: UserRole
    is_active: bool
    onboarding_completed_at: datetime | None
    created_at: datetime


class UserUpdateIn(BaseModel):
    is_active: bool | None = None
    role: UserRole | None = None


class LegalDocOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_type: LegalDocType
    version: int
    content: str
    is_active: bool
    created_at: datetime


class LegalDocCreateIn(BaseModel):
    doc_type: LegalDocType = LegalDocType.TERMS
    content: str
    activate: bool = True
