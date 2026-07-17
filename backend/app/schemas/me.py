"""Schemas for the client dashboard (/me) endpoints."""

from datetime import date, datetime

from pydantic import BaseModel, Field


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
    reminders_enabled: bool
    dietary_restrictions: list[str]
    allergies: list[str]
    target_calories: int | None
    target_protein_g: float | None
    target_carbs_g: float | None
    target_fat_g: float | None
    target_fiber_g: float | None
    target_water_ml: int | None


class ProfileUpdateIn(BaseModel):
    """Partial update of the account + nutrition profile. All fields optional."""

    full_name: str | None = None
    sex: str | None = None
    birth_date: date | None = None
    height_cm: float | None = None
    current_weight_kg: float | None = None
    activity_level: str | None = None
    goal: str | None = None
    target_weight_kg: float | None = None
    weekly_rate_kg: float | None = None
    timezone: str | None = None
    reminders_enabled: bool | None = None
    dietary_restrictions: list[str] | None = None
    allergies: list[str] | None = None


class DietPlanItemOut(BaseModel):
    id: int
    scheduled_date: date | None
    meal_type: str | None
    scheduled_time: str | None
    title: str
    description: str | None
    calories: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    fiber_g: float | None
    status: str
    source: str


class DietPlanItemCreate(BaseModel):
    title: str
    scheduled_date: date | None = None
    # Optional weekday hint (0=Mon … 6=Sun); resolved to the nearest date.
    weekday: int | None = Field(default=None, ge=0, le=6)
    meal_type: str | None = None
    scheduled_time: str | None = None
    description: str | None = None
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    status: str | None = None


class DietPlanItemUpdate(BaseModel):
    title: str | None = None
    scheduled_date: date | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)
    meal_type: str | None = None
    scheduled_time: str | None = None
    description: str | None = None
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    status: str | None = None


class ReminderOut(BaseModel):
    id: int
    type: str
    message: str | None
    time: str
    days_of_week: list[int]
    enabled: bool
    source: str


class ReminderCreate(BaseModel):
    type: str
    time: str
    message: str | None = None
    days_of_week: list[int] | None = None
    enabled: bool = True


class ReminderUpdate(BaseModel):
    type: str | None = None
    time: str | None = None
    message: str | None = None
    days_of_week: list[int] | None = None
    enabled: bool | None = None


class NoteOut(BaseModel):
    id: int
    category: str
    content: str
    source: str


class NoteCreate(BaseModel):
    content: str
    category: str | None = None


class WeightPointOut(BaseModel):
    logged_at: datetime
    weight_kg: float


class WaterPointOut(BaseModel):
    logged_at: datetime
    amount_ml: float


class WaterLogCreate(BaseModel):
    amount_ml: float = Field(gt=0)


class ConversationOut(BaseModel):
    id: int
    title: str | None
    created_at: datetime
    message_count: int


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime
