"""Thin async client for Gemini Vision API (free tier: 1500 req/day)."""

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_FOOD_ANALYSIS_PROMPT = """Analiza esta foto de comida o bebida. Responde en español, solo con estos datos:

- Plato: [nombre del plato]
- Ingredientes: [lista breve]
- Cantidad estimada: [aprox en gramos o unidades]
- Calorias: [X] kcal
- Proteina: [X]g
- Carbohidratos: [X]g
- Grasa: [X]g
- Fibra: [X]g

Sé breve y honesto. Si no puedes identificar algo, di "No estoy seguro". Usa rangos cuando no puedas precisar."""


async def analyze_food_image(
    image_base64: str,
    mime_type: str = "image/jpeg",
    conversation_context: str | None = None,
) -> str:
    """Send a food photo to Gemini 2.0 Flash and return the analysis text.

    ``conversation_context`` — recent chat turns, if any — is prepended so
    Gemini can use what the user already said (e.g. "es la cena de ayer",
    "esto lo compré en el super") instead of guessing from the pixels alone.

    Returns a plain-text analysis suitable for Telegram display.
    """
    if not settings.gemini_api_key:
        return (
            "No tengo configurada la clave de Gemini Vision. "
            "Puedes describirme la comida y te ayudo igualmente."
        )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_vision_model}:generateContent"
        f"?key={settings.gemini_api_key}"
    )

    prompt = _FOOD_ANALYSIS_PROMPT
    if conversation_context:
        prompt = (
            "Contexto: fragmento reciente de la conversación con el usuario "
            f"(puede ser irrelevante para esta foto, ignóralo si no aplica):\n"
            f"{conversation_context}\n\n{_FOOD_ANALYSIS_PROMPT}"
        )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_base64,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 500,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        logger.error("Unexpected Gemini response: %s", data)
        return "No pude analizar la foto. ¿Puedes describirme la comida?"

    return text.strip()
