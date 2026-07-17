"""ORM models package.

Importing every model here ensures they are registered on ``Base.metadata``
so Alembic autogeneration can see them.
"""

from app.models.app_settings import AppSettings
from app.models.conversation import Conversation, Message
from app.models.diet_plan import DietPlanItem
from app.models.food_cache import FoodCache
from app.models.knowledge import KnowledgeDocument, KnowledgeEmbedding
from app.models.legal import LegalDocument, UserConsent
from app.models.login_code import LoginCode
from app.models.meal_log import MealLog
from app.models.nutrition_profile import NutritionProfile
from app.models.reminder import Reminder
from app.models.user import User
from app.models.user_note import UserNote
from app.models.water_log import WaterLog
from app.models.weight_log import WeightLog

__all__ = [
    "User",
    "NutritionProfile",
    "Conversation",
    "Message",
    "MealLog",
    "WeightLog",
    "WaterLog",
    "DietPlanItem",
    "UserNote",
    "Reminder",
    "KnowledgeDocument",
    "KnowledgeEmbedding",
    "FoodCache",
    "LegalDocument",
    "UserConsent",
    "LoginCode",
    "AppSettings",
]
