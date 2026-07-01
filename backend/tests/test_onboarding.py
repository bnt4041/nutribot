"""Unit tests for onboarding pure logic (no DB required)."""

from datetime import date
from decimal import Decimal

from app.models.enums import Goal
from app.models.nutrition_profile import NutritionProfile
from app.services import onboarding


def test_parse_decimal_accepts_comma_and_dot():
    assert onboarding._parse_decimal("72.5") == Decimal("72.5")
    assert onboarding._parse_decimal("72,5") == Decimal("72.5")
    assert onboarding._parse_decimal("  80 ") == Decimal("80")


def test_parse_decimal_rejects_garbage():
    assert onboarding._parse_decimal("abc") is None
    assert onboarding._parse_decimal("") is None


def test_parse_birth_date_valid_formats():
    assert onboarding._parse_birth_date("15/06/1990") == date(1990, 6, 15)
    assert onboarding._parse_birth_date("1990-06-15") == date(1990, 6, 15)


def test_parse_birth_date_rejects_bad_input_and_implausible_age():
    assert onboarding._parse_birth_date("no soy fecha") is None
    # A newborn / future-ish date is out of the accepted 10-120 age range.
    assert onboarding._parse_birth_date(date.today().strftime("%d/%m/%Y")) is None


def test_next_step_skips_target_and_rate_when_maintaining():
    profile = NutritionProfile(goal=Goal.MAINTAIN)
    # After "goal", the next applicable step must skip target_weight/weekly_rate.
    nxt = onboarding._next_step(profile, "goal")
    assert nxt is not None
    assert nxt.key == "dietary_restrictions"


def test_next_step_includes_target_and_rate_when_losing():
    profile = NutritionProfile(goal=Goal.LOSE)
    nxt = onboarding._next_step(profile, "goal")
    assert nxt is not None
    assert nxt.key == "target_weight"


def test_first_step_is_sex():
    profile = NutritionProfile()
    assert onboarding._next_step(profile, None).key == "sex"
