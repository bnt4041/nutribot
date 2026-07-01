"""Tests for macro target computation and meal macro scaling."""

from datetime import date

import pytest

from app.models.enums import ActivityLevel, Goal, Sex
from app.models.nutrition_profile import NutritionProfile
from app.services.nutrition.targets import bmr_mifflin, compute_targets
from app.services.nutrition.tracking import scale_macros


def test_bmr_mifflin_known_values():
    # Man, 80 kg, 180 cm, 30 y: 10*80 + 6.25*180 - 5*30 + 5 = 1780
    assert bmr_mifflin(Sex.MALE, 80, 180, 30) == pytest.approx(1780)
    # Woman, 60 kg, 165 cm, 30 y: 600 + 1031.25 - 150 - 161 = 1320.25
    assert bmr_mifflin(Sex.FEMALE, 60, 165, 30) == pytest.approx(1320.25)


def _profile(**kw) -> NutritionProfile:
    defaults = dict(
        sex=Sex.MALE,
        birth_date=date(1994, 1, 1),
        height_cm=180,
        current_weight_kg=80,
        activity_level=ActivityLevel.MODERATE,
        goal=Goal.MAINTAIN,
        weekly_rate_kg=None,
    )
    defaults.update(kw)
    return NutritionProfile(**defaults)


def test_compute_targets_maintain_matches_tdee():
    targets = compute_targets(_profile(goal=Goal.MAINTAIN))
    assert targets is not None
    # BMR (~1780 at age ~32) * 1.55 activity; allow a small age-dependent range.
    assert 2600 <= targets.calories <= 2800
    # Protein at 1.8 g/kg * 80 = 144 g.
    assert targets.protein_g == pytest.approx(144.0, abs=0.5)


def test_lose_goal_creates_deficit():
    maintain = compute_targets(_profile(goal=Goal.MAINTAIN))
    lose = compute_targets(_profile(goal=Goal.LOSE, weekly_rate_kg=0.5))
    # 0.5 kg/week -> ~550 kcal/day deficit.
    assert maintain.calories - lose.calories == pytest.approx(550, abs=2)
    assert lose.protein_g == pytest.approx(160.0, abs=0.5)  # 2.0 g/kg


def test_calorie_floor_is_respected():
    tiny = compute_targets(
        _profile(current_weight_kg=45, goal=Goal.LOSE, weekly_rate_kg=2)
    )
    assert tiny.calories >= 1200


def test_compute_targets_returns_none_when_incomplete():
    assert compute_targets(_profile(height_cm=None)) is None


def test_scale_macros_half_portion():
    per_100g = {
        "calories_100g": 100,
        "protein_100g": 10,
        "carbs_100g": 5,
        "fat_100g": 2,
    }
    scaled = scale_macros(per_100g, 50)
    assert scaled == {
        "calories": 50.0,
        "protein_g": 5.0,
        "carbs_g": 2.5,
        "fat_g": 1.0,
    }


def test_scale_macros_handles_missing_values():
    scaled = scale_macros({"calories_100g": 200, "protein_100g": None}, 250)
    assert scaled["calories"] == 500.0
    assert scaled["protein_g"] is None
