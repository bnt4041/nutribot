"""Schemas for admin dashboard endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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
    last_message_at: datetime | None = None
    tokens_total: int = 0
    estimated_cost_usd: float = 0.0


class UserUpdateIn(BaseModel):
    is_active: bool | None = None
    role: UserRole | None = None


class AppSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inactivity_reminder_enabled: bool
    inactivity_reminder_days: int


class AppSettingsUpdateIn(BaseModel):
    inactivity_reminder_enabled: bool | None = None
    inactivity_reminder_days: int | None = Field(default=None, ge=1, le=90)


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
