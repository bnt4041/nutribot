"""Daily calorie and macro target calculation (Mifflin-St Jeor + goal)."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActivityLevel, Goal, Sex
from app.models.nutrition_profile import NutritionProfile

# TDEE multipliers by activity level.
ACTIVITY_FACTORS: dict[ActivityLevel, float] = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHT: 1.375,
    ActivityLevel.MODERATE: 1.55,
    ActivityLevel.ACTIVE: 1.725,
    ActivityLevel.VERY_ACTIVE: 1.9,
}

# Protein grams per kg of bodyweight by goal.
PROTEIN_PER_KG: dict[Goal, float] = {
    Goal.LOSE: 2.0,
    Goal.MAINTAIN: 1.8,
    Goal.GAIN: 2.0,
}

FAT_CALORIE_FRACTION = 0.25  # 25% of calories from fat
KCAL_PER_KG = 7700  # approx energy in 1 kg of body mass
CALORIE_FLOOR = 1200  # never recommend below this
FIBER_PER_1000_KCAL = 14.0  # g fiber per 1000 kcal (Institute of Medicine guideline)
FIBER_FLOOR = 25.0  # never recommend below this
WATER_ML_PER_KG = 35  # ml of water per kg of bodyweight


@dataclass
class Targets:
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    water_ml: int


def _age(birth: date) -> int:
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def bmr_mifflin(sex: Sex, weight_kg: float, height_cm: float, age: int) -> float:
    """Mifflin-St Jeor basal metabolic rate (kcal/day)."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == Sex.MALE else base - 161


def compute_targets(profile: NutritionProfile) -> Targets | None:
    """Compute daily targets from a profile, or None if data is insufficient."""
    if (
        profile.sex is None
        or profile.birth_date is None
        or profile.height_cm is None
        or profile.current_weight_kg is None
        or profile.activity_level is None
        or profile.goal is None
    ):
        return None

    weight = float(profile.current_weight_kg)
    height = float(profile.height_cm)
    age = _age(profile.birth_date)

    bmr = bmr_mifflin(profile.sex, weight, height, age)
    tdee = bmr * ACTIVITY_FACTORS[profile.activity_level]

    # Adjust calories by the desired weekly rate (kg/week).
    rate = float(profile.weekly_rate_kg) if profile.weekly_rate_kg is not None else 0.0
    daily_adjustment = rate * KCAL_PER_KG / 7
    if profile.goal == Goal.LOSE:
        calories = tdee - daily_adjustment
    elif profile.goal == Goal.GAIN:
        calories = tdee + daily_adjustment
    else:
        calories = tdee
    calories = max(calories, CALORIE_FLOOR)

    protein_g = PROTEIN_PER_KG[profile.goal] * weight
    fat_g = (calories * FAT_CALORIE_FRACTION) / 9
    remaining = calories - (protein_g * 4 + fat_g * 9)
    carbs_g = max(remaining / 4, 0.0)
    fiber_g = max(calories / 1000 * FIBER_PER_1000_KCAL, FIBER_FLOOR)
    water_ml = weight * WATER_ML_PER_KG

    return Targets(
        calories=round(calories),
        protein_g=round(protein_g, 1),
        carbs_g=round(carbs_g, 1),
        fat_g=round(fat_g, 1),
        fiber_g=round(fiber_g, 1),
        water_ml=round(water_ml),
    )


async def ensure_targets(db: AsyncSession, profile: NutritionProfile) -> Targets | None:
    """Compute and persist targets if missing; return them either way.

    All cached fields must be present to use the fast path — if a target was
    added after the profile's targets were first cached (e.g. fiber/water),
    only the older fields would be set, so we fall through and recompute.
    """
    cached_fields = (
        profile.target_calories,
        profile.target_protein_g,
        profile.target_carbs_g,
        profile.target_fat_g,
        profile.target_fiber_g,
        profile.target_water_ml,
    )
    if all(f is not None for f in cached_fields):
        return Targets(
            calories=profile.target_calories,
            protein_g=float(profile.target_protein_g),
            carbs_g=float(profile.target_carbs_g),
            fat_g=float(profile.target_fat_g),
            fiber_g=float(profile.target_fiber_g),
            water_ml=profile.target_water_ml,
        )
    targets = compute_targets(profile)
    if targets is None:
        return None
    profile.target_calories = targets.calories
    profile.target_protein_g = targets.protein_g
    profile.target_carbs_g = targets.carbs_g
    profile.target_fat_g = targets.fat_g
    profile.target_fiber_g = targets.fiber_g
    profile.target_water_ml = targets.water_ml
    await db.flush()
    return targets


async def recompute_targets(db: AsyncSession, profile: NutritionProfile) -> Targets | None:
    """Clear cached targets and recompute from the (updated) profile.

    Use this after any change to the metrics that feed the calculation (weight,
    height, age, activity, goal, weekly rate) so daily targets stay in sync.
    """
    profile.target_calories = None
    profile.target_protein_g = None
    profile.target_carbs_g = None
    profile.target_fat_g = None
    profile.target_fiber_g = None
    profile.target_water_ml = None
    return await ensure_targets(db, profile)
