"""Schemas for the client dashboard (/me) endpoints."""

from datetime import date, datetime

from pydantic import BaseModel


class ProfileOut(BaseModel):
    full_name: str | None
    email: str | None
    telegram_id: int | None
    onboarding_completed: bool
    sex: str | None
    birth_date: date | None
    height_cm: float | None
    current_weight_kg: float | None
    target_weight_kg: float | None
    weekly_rate_kg: float | None
    activity_level: str | None
    goal: str | None
    timezone: str | None
    dietary_restrictions: list[str]
    allergies: list[str]
    target_calories: int | None
    target_protein_g: float | None
    target_carbs_g: float | None
    target_fat_g: float | None


class WeightPointOut(BaseModel):
    logged_at: datetime
    weight_kg: float


class ConversationOut(BaseModel):
    id: int
    title: str | None
    created_at: datetime
    message_count: int


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime
