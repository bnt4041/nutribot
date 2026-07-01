"""Guided onboarding: a button-driven questionnaire that builds the profile.

The backend is the source of truth for progress. ``User.onboarding_step`` holds
the key of the step currently awaiting an answer; each answer is validated and
persisted incrementally, then the machine advances to the next applicable step.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActivityLevel, Goal, Sex
from app.models.nutrition_profile import NutritionProfile
from app.models.user import User
from app.models.weight_log import WeightLog
from app.schemas.bot import BotButton, BotReply
from app.services.nutrition.targets import ensure_targets

# Sentinels used as button values in list-style steps.
NONE_VALUE = "__none__"
DONE_VALUE = "__done__"


@dataclass
class Choice:
    label: str
    value: str


@dataclass
class Step:
    key: str
    kind: str  # choice | number | text_list | multi | timezone
    prompt: str
    choices: list[Choice] = field(default_factory=list)
    # Common preset buttons for multi steps (besides done/none).
    presets: list[Choice] = field(default_factory=list)

    def applies(self, profile: NutritionProfile) -> bool:  # noqa: D401
        """Whether this step is relevant given the profile so far."""
        if self.key in ("target_weight", "weekly_rate"):
            return profile.goal is not None and profile.goal != Goal.MAINTAIN
        return True


STEPS: list[Step] = [
    Step(
        key="sex",
        kind="choice",
        prompt="Para crear tu ficha, empecemos. ¿Cuál es tu sexo biológico?",
        choices=[Choice("Hombre", "male"), Choice("Mujer", "female")],
    ),
    Step(
        key="birth_date",
        kind="text",
        prompt="¿Cuál es tu fecha de nacimiento? Escríbela en formato DD/MM/AAAA.",
    ),
    Step(
        key="height_cm",
        kind="number",
        prompt="¿Cuánto mides? Indícalo en centímetros (ej. 175).",
    ),
    Step(
        key="weight",
        kind="number",
        prompt="¿Cuánto pesas actualmente? Indícalo en kilos (ej. 72.5).",
    ),
    Step(
        key="activity_level",
        kind="choice",
        prompt="¿Cuál es tu nivel de actividad física habitual?",
        choices=[
            Choice("Sedentario", "sedentary"),
            Choice("Ligera", "light"),
            Choice("Moderada", "moderate"),
            Choice("Alta", "active"),
            Choice("Muy alta", "very_active"),
        ],
    ),
    Step(
        key="goal",
        kind="choice",
        prompt="¿Cuál es tu objetivo principal?",
        choices=[
            Choice("Perder grasa", "lose"),
            Choice("Mantener", "maintain"),
            Choice("Ganar músculo", "gain"),
        ],
    ),
    Step(
        key="target_weight",
        kind="number",
        prompt="¿Qué peso te gustaría alcanzar? Indícalo en kilos.",
    ),
    Step(
        key="weekly_rate",
        kind="number",
        prompt=(
            "¿A qué ritmo semanal quieres avanzar? Indica los kilos por semana "
            "(ej. 0.5). Un ritmo moderado suele ser 0.25-0.75 kg/semana."
        ),
    ),
    Step(
        key="dietary_restrictions",
        kind="multi",
        prompt=(
            "¿Sigues alguna dieta o restricción? Pulsa las que apliquen (o escribe "
            "otra), y luego «Terminar». Si no tienes, pulsa «Ninguna»."
        ),
        presets=[
            Choice("Vegetariano", "vegetariano"),
            Choice("Vegano", "vegano"),
            Choice("Sin gluten", "sin gluten"),
            Choice("Sin lactosa", "sin lactosa"),
            Choice("Keto", "keto"),
        ],
    ),
    Step(
        key="allergies",
        kind="text_list",
        prompt=(
            "¿Tienes alergias o intolerancias alimentarias? Escríbelas separadas "
            "por comas (ej. frutos secos, marisco), o pulsa «Ninguna»."
        ),
    ),
    Step(
        key="timezone",
        kind="timezone",
        prompt=(
            "¿En qué zona horaria estás? Sirve para calcular tu día nutricional. "
            "Elige una o escribe tu zona IANA (ej. America/Mexico_City)."
        ),
        choices=[
            Choice("España (península)", "Europe/Madrid"),
            Choice("Canarias", "Atlantic/Canary"),
        ],
    ),
    Step(
        key="reminders",
        kind="choice",
        prompt="¿Quieres activar recordatorios para registrar comidas y pesarte?",
        choices=[Choice("Sí", "yes"), Choice("No", "no")],
    ),
]

STEP_BY_KEY = {s.key: s for s in STEPS}


def _step_view(step: Step) -> BotReply:
    """Render a step as a BotReply (prompt + buttons)."""
    if step.kind == "choice" or step.kind == "timezone":
        buttons = [BotButton(label=c.label, value=f"ob:{step.key}:{c.value}") for c in step.choices]
        allow_free = step.kind == "timezone"  # timezone also accepts typed IANA name
        return BotReply(text=step.prompt, buttons=buttons, allow_free_text=allow_free)
    if step.kind == "multi":
        buttons = [
            BotButton(label=c.label, value=f"ob:{step.key}:{c.value}") for c in step.presets
        ]
        buttons.append(BotButton(label="✅ Terminar", value=f"ob:{step.key}:{DONE_VALUE}"))
        buttons.append(BotButton(label="Ninguna", value=f"ob:{step.key}:{NONE_VALUE}"))
        return BotReply(text=step.prompt, buttons=buttons, allow_free_text=True)
    if step.kind == "text_list":
        return BotReply(
            text=step.prompt,
            buttons=[BotButton(label="Ninguna", value=f"ob:{step.key}:{NONE_VALUE}")],
            allow_free_text=True,
        )
    # number / text
    return BotReply(text=step.prompt, buttons=[], allow_free_text=True)


def _next_step(profile: NutritionProfile, after_key: str | None) -> Step | None:
    """First applicable step after ``after_key`` (or from the start)."""
    started = after_key is None
    for step in STEPS:
        if not started:
            if step.key == after_key:
                started = True
            continue
        if step.applies(profile):
            return step
    return None


async def _ensure_profile(db: AsyncSession, user: User) -> NutritionProfile:
    result = await db.execute(
        select(NutritionProfile).where(NutritionProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is not None:
        return profile
    profile = NutritionProfile(user_id=user.id)
    db.add(profile)
    await db.flush()
    return profile


def current_view(user: User) -> BotReply | None:
    """Re-render the step the user is currently on (for /start re-entry)."""
    step = STEP_BY_KEY.get(user.onboarding_step or "")
    return _step_view(step) if step else None


async def start(db: AsyncSession, user: User) -> BotReply:
    """Begin onboarding: create the profile and show the first step."""
    profile = await _ensure_profile(db, user)
    first = _next_step(profile, None)
    assert first is not None
    user.onboarding_step = first.key
    await db.flush()
    intro = "¡Gracias! 🙌 Vamos a preparar tu perfil con unas preguntas rápidas.\n\n"
    view = _step_view(first)
    return BotReply(
        text=intro + view.text, buttons=view.buttons, allow_free_text=view.allow_free_text
    )


def _parse_decimal(raw: str) -> Decimal | None:
    try:
        value = Decimal(raw.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None
    return value


# Plausible ranges for numeric answers: (min, max).
_NUM_RANGES = {
    "height_cm": (Decimal("80"), Decimal("250")),
    "weight": (Decimal("20"), Decimal("400")),
    "target_weight": (Decimal("20"), Decimal("400")),
    "weekly_rate": (Decimal("0.05"), Decimal("2")),
}


def _error(step: Step, message: str) -> BotReply:
    view = _step_view(step)
    return BotReply(
        text=f"{message}\n\n{view.text}",
        buttons=view.buttons,
        allow_free_text=view.allow_free_text,
    )


async def _apply_answer(
    db: AsyncSession,
    user: User,
    profile: NutritionProfile,
    step: Step,
    text: str | None,
    value: str | None,
) -> tuple[bool, BotReply | None]:
    """Validate and persist the answer for ``step``.

    Returns (advanced, error_reply). When advanced is False the error_reply
    should be sent and the step stays the same.
    """
    if step.kind == "choice":
        if value is None:
            return False, _error(step, "Por favor, pulsa una de las opciones.")
        if step.key == "sex":
            profile.sex = Sex(value)
        elif step.key == "activity_level":
            profile.activity_level = ActivityLevel(value)
        elif step.key == "goal":
            profile.goal = Goal(value)
        elif step.key == "reminders":
            profile.reminders_enabled = value == "yes"
        return True, None

    if step.kind == "timezone":
        tz = value or (text.strip() if text else "")
        try:
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError):
            return False, _error(step, "No reconozco esa zona horaria.")
        profile.timezone = tz
        return True, None

    if step.kind == "number":
        if not text:
            return False, _error(step, "Escríbeme el número, por favor.")
        num = _parse_decimal(text)
        if num is None:
            return False, _error(step, "No parece un número válido.")
        lo, hi = _NUM_RANGES[step.key]
        if not (lo <= num <= hi):
            return False, _error(step, f"Debe estar entre {lo} y {hi}.")
        if step.key == "height_cm":
            profile.height_cm = num
        elif step.key == "weight":
            profile.current_weight_kg = num
            db.add(WeightLog(user_id=user.id, weight_kg=num))  # seed weight history
        elif step.key == "target_weight":
            profile.target_weight_kg = num
        elif step.key == "weekly_rate":
            profile.weekly_rate_kg = num
        return True, None

    if step.kind == "text":  # birth_date
        if not text:
            return False, _error(step, "Escríbeme la fecha, por favor.")
        parsed = _parse_birth_date(text)
        if parsed is None:
            return False, _error(step, "Formato no válido. Usa DD/MM/AAAA.")
        profile.birth_date = parsed
        return True, None

    if step.kind == "text_list":  # allergies
        if value == NONE_VALUE:
            profile.allergies = []
        elif text:
            profile.allergies = [t.strip() for t in text.split(",") if t.strip()]
        else:
            return False, _error(step, "Escríbelas separadas por comas o pulsa «Ninguna».")
        return True, None

    if step.kind == "multi":  # dietary_restrictions
        if value == DONE_VALUE:
            return True, None
        if value == NONE_VALUE:
            profile.dietary_restrictions = []
            return True, None
        # A preset tap or free text adds an item and stays on the step.
        item = None
        if value is not None:
            item = value
        elif text:
            item = text.strip()
        if item:
            current = list(profile.dietary_restrictions or [])
            if item not in current:
                current.append(item)
            profile.dietary_restrictions = current
        selected = ", ".join(profile.dietary_restrictions) or "ninguna"
        view = _step_view(step)
        return False, BotReply(
            text=f"Seleccionadas: {selected}.\nAñade más o pulsa «Terminar».",
            buttons=view.buttons,
            allow_free_text=True,
        )

    return True, None


def _parse_birth_date(text: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
        age = (date.today() - parsed).days / 365.25
        if 10 <= age <= 120:
            return parsed
        return None
    return None


async def _finish(db: AsyncSession, user: User, profile: NutritionProfile) -> BotReply:
    user.onboarding_step = None
    user.onboarding_completed_at = datetime.now(timezone.utc)
    # Compute and persist daily calorie/macro targets from the completed profile.
    await ensure_targets(db, profile)
    await db.flush()
    return BotReply(
        text=(
            "¡Perfecto, tu ficha está lista! ✅\n\n"
            "Ya puedes preguntarme lo que quieras sobre nutrición, o contarme qué "
            "comes para llevar el control. ¿En qué te ayudo?"
        )
    )


async def process(
    db: AsyncSession,
    user: User,
    text: str | None,
    action_value: str | None,
) -> BotReply:
    """Advance onboarding using the user's latest input.

    ``action_value`` is the part after ``ob:<step>:`` from a button tap, already
    matched to the current step by the caller (None for free text).
    """
    profile = await _ensure_profile(db, user)
    current = STEP_BY_KEY.get(user.onboarding_step or "")
    if current is None:
        # Defensive: no known step -> (re)start.
        return await start(db, user)

    advanced, error = await _apply_answer(db, user, profile, current, text, action_value)
    if not advanced:
        assert error is not None
        return error

    nxt = _next_step(profile, current.key)
    if nxt is None:
        return await _finish(db, user, profile)

    user.onboarding_step = nxt.key
    await db.flush()
    return _step_view(nxt)
