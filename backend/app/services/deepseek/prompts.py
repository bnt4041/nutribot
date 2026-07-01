"""System prompts for the DeepSeek assistant."""

from datetime import date

from app.models.enums import ActivityLevel, Goal, Sex
from app.models.nutrition_profile import NutritionProfile

# User-facing persona speaks Spanish (per project conventions).
NUTRITION_SYSTEM_PROMPT = """Eres NutriBot, un asistente de nutrición conversacional \
y cercano. Ayudas a las personas a comer mejor, entender los macronutrientes y \
alcanzar sus objetivos (perder grasa, mantener o ganar masa muscular).

Directrices:
- Responde siempre en español, de forma clara y motivadora.
- Da consejos prácticos y basados en evidencia; evita afirmaciones médicas tajantes.
- No diagnostiques ni sustituyas a un profesional sanitario. Ante dudas médicas \
serias (patologías, medicación, trastornos alimentarios), recomienda acudir a un \
médico o dietista-nutricionista colegiado.
- Sé conciso salvo que el usuario pida detalle.
- Cuando necesites datos nutricionales concretos de un alimento o producto \
(calorías o macros), usa las herramientas de búsqueda de alimentos disponibles en \
lugar de inventar cifras. Si el usuario da un código de barras, búscalo por código.
- Cuando informes de un producto concreto encontrado, incluye al final su enlace \
(campo "url") en una línea aparte, tal cual, sin formato. Así el usuario puede ver \
la ficha y la foto del producto.
- Usa los datos de la ficha del usuario que se indican más abajo. NO vuelvas a \
preguntar información que ya tienes (objetivo, peso, altura, restricciones, alergias); \
úsala directamente. Solo pregunta si falta un dato que necesites de verdad.

FORMATO (importante, el usuario lee en Telegram):
- Escribe en texto plano y natural, como en un chat. Frases cortas.
- NO uses Markdown: nada de asteriscos para negrita (**), ni almohadillas (#), \
ni tablas. Los símbolos se ven feos en Telegram.
- Si necesitas enumerar, usa guiones simples (-) y pocos elementos.
- Puedes usar algún emoji con moderación."""


_SEX_ES = {Sex.MALE: "hombre", Sex.FEMALE: "mujer"}
_GOAL_ES = {
    Goal.LOSE: "perder grasa",
    Goal.MAINTAIN: "mantener peso",
    Goal.GAIN: "ganar masa muscular",
}
_ACTIVITY_ES = {
    ActivityLevel.SEDENTARY: "sedentaria",
    ActivityLevel.LIGHT: "ligera",
    ActivityLevel.MODERATE: "moderada",
    ActivityLevel.ACTIVE: "alta",
    ActivityLevel.VERY_ACTIVE: "muy alta",
}


def _age_from(birth: date) -> int:
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def build_system_prompt(profile: NutritionProfile | None) -> str:
    """Base persona plus a summary of the user's profile, when available."""
    if profile is None:
        return NUTRITION_SYSTEM_PROMPT

    lines: list[str] = []
    if profile.sex is not None:
        lines.append(f"- Sexo: {_SEX_ES.get(profile.sex, profile.sex.value)}")
    if profile.birth_date is not None:
        lines.append(f"- Edad: {_age_from(profile.birth_date)} años")
    if profile.height_cm is not None:
        lines.append(f"- Altura: {profile.height_cm} cm")
    if profile.current_weight_kg is not None:
        lines.append(f"- Peso actual: {profile.current_weight_kg} kg")
    if profile.goal is not None:
        lines.append(f"- Objetivo: {_GOAL_ES.get(profile.goal, profile.goal.value)}")
    if profile.target_weight_kg is not None:
        lines.append(f"- Peso objetivo: {profile.target_weight_kg} kg")
    if profile.weekly_rate_kg is not None:
        lines.append(f"- Ritmo deseado: {profile.weekly_rate_kg} kg/semana")
    if profile.activity_level is not None:
        lines.append(
            f"- Actividad física: {_ACTIVITY_ES.get(profile.activity_level, profile.activity_level.value)}"
        )
    if profile.dietary_restrictions:
        lines.append(f"- Restricciones/dieta: {', '.join(profile.dietary_restrictions)}")
    if profile.allergies:
        lines.append(f"- Alergias/intolerancias: {', '.join(profile.allergies)}")

    if not lines:
        return NUTRITION_SYSTEM_PROMPT

    profile_block = "\n\nFicha del usuario (úsala, no la vuelvas a preguntar):\n" + "\n".join(lines)
    return NUTRITION_SYSTEM_PROMPT + profile_block
