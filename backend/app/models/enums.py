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


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


class LegalDocType(str, enum.Enum):
    TERMS = "terms"
    PRIVACY = "privacy"
