"""DeepSeek function-calling tools: food lookups + meal tracking."""

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.nutrition import tracking
from app.services.openfoodfacts import service as off_service

# OpenAI-format tool schemas exposed to the model.
FOOD_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_food_by_name",
            "description": (
                "Busca alimentos por nombre en Open Food Facts y devuelve sus "
                "macronutrientes por 100 g. Úsalo cuando el usuario menciona un "
                "alimento por su nombre y necesitas datos nutricionales."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Nombre del alimento a buscar, ej. 'yogur griego'.",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_food_by_barcode",
            "description": (
                "Obtiene un producto por su código de barras en Open Food Facts, "
                "con sus macronutrientes por 100 g."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "barcode": {
                        "type": "string",
                        "description": "Código de barras (EAN/UPC) del producto.",
                    }
                },
                "required": ["barcode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_meal",
            "description": (
                "Registra una comida o bebida que el usuario dice haber tomado. "
                "Úsala cuando el usuario quiera apuntar lo que ha comido. Si conoces "
                "el código de barras del producto, pásalo y se obtendrán macros "
                "exactos; si no, calcula tú los macros TOTALES de la porción y "
                "pásalos en calories/protein_g/carbs_g/fat_g."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "food_name": {
                        "type": "string",
                        "description": "Nombre del alimento, ej. '2 huevos revueltos'.",
                    },
                    "quantity_g": {
                        "type": "number",
                        "description": "Cantidad en gramos o ml, si se conoce.",
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "snack"],
                        "description": "Tipo de comida, si el usuario lo indica.",
                    },
                    "barcode": {
                        "type": "string",
                        "description": "Código de barras del producto, si se conoce.",
                    },
                    "calories": {"type": "number", "description": "Kcal totales de la porción."},
                    "protein_g": {"type": "number", "description": "Proteína (g) total."},
                    "carbs_g": {"type": "number", "description": "Carbohidratos (g) total."},
                    "fat_g": {"type": "number", "description": "Grasa (g) total."},
                },
                "required": ["food_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_summary",
            "description": (
                "Devuelve el resumen nutricional del día del usuario: total "
                "consumido, objetivos y lo que le queda. Úsala cuando pregunte por "
                "su progreso, cuánto le queda o qué ha comido hoy."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def make_food_tool_executor(
    db: AsyncSession, user: User
) -> Callable[[str, dict], Awaitable[object]]:
    """Bind the tools to a database session and the current user."""

    async def execute(name: str, arguments: dict) -> object:
        if name == "search_food_by_name":
            query = (arguments.get("name") or "").strip()
            if not query:
                return {"error": "missing 'name'"}
            results = await off_service.search(db, query)
            return {"results": results} if results else {"results": [], "message": "sin resultados"}
        if name == "get_food_by_barcode":
            barcode = (arguments.get("barcode") or "").strip()
            if not barcode:
                return {"error": "missing 'barcode'"}
            product = await off_service.get_by_barcode(db, barcode)
            return product or {"error": "producto no encontrado"}
        if name == "log_meal":
            food_name = (arguments.get("food_name") or "").strip()
            if not food_name:
                return {"error": "missing 'food_name'"}
            return await tracking.log_meal(
                db,
                user,
                food_name=food_name,
                quantity_g=arguments.get("quantity_g"),
                meal_type=arguments.get("meal_type"),
                barcode=arguments.get("barcode"),
                calories=arguments.get("calories"),
                protein_g=arguments.get("protein_g"),
                carbs_g=arguments.get("carbs_g"),
                fat_g=arguments.get("fat_g"),
            )
        if name == "get_daily_summary":
            return await tracking.daily_summary(db, user)
        return {"error": f"unknown tool: {name}"}

    return execute
