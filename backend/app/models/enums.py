"""Shared enumerations used across ORM models."""

import enum


class UserRole(str, enum.Enum):
    CLIENT = "client"
    ADMIN = "admin"


class Sex(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(str, enum.Enum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"


class Goal(str, enum.Enum):
    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MealType(str, enum.Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class DietItemStatus(str, enum.Enum):
    """Lifecycle of a recommended diet-plan item."""

    PROPOSED = "proposed"  # suggested by the AI, awaiting the user's confirmation
    CONFIRMED = "confirmed"  # accepted by the user (via chat or dashboard)


class NoteCategory(str, enum.Enum):
    """Kind of "a tener en cuenta" note the AI keeps about a user."""

    DISLIKE = "dislike"  # foods/things the user dislikes or avoids
    LIKE = "like"  # foods/things the user enjoys
    MEDICAL = "medical"  # medical/health considerations worth remembering
    HABIT = "habit"  # routines, schedules, lifestyle habits
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


class LegalDocType(str, enum.Enum):
    TERMS = "terms"
    PRIVACY = "privacy"
