"""DeepSeek function-calling tools: food lookups, meal tracking, profile & plan."""

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import DietItemStatus
from app.models.user import User
from app.services import preferences
from app.services import profile as profile_service
from app.services.nutrition import diet_plan, tracking
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
    {
        "type": "function",
        "function": {
            "name": "remember_preference",
            "description": (
                "Guarda algo relevante que hay que tener en cuenta sobre el usuario "
                "para futuras respuestas y propuestas: gustos, cosas que no le gustan "
                "o evita (ej. 'no le gusta la pera'), consideraciones de salud, o "
                "hábitos. Úsala cuando detectes una preferencia o dato así en la "
                "conversación, aunque el usuario no lo pida explícitamente. No "
                "guardes duplicados de lo que ya está en su ficha."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "La nota, redactada de forma breve y clara.",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["dislike", "like", "medical", "habit", "other"],
                        "description": (
                            "Tipo: dislike (no le gusta/evita), like (le gusta), "
                            "medical (salud), habit (hábito), other."
                        ),
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_profile",
            "description": (
                "Actualiza los datos o los objetivos del usuario cuando lo pide "
                "(ej. cambia su peso actual, su objetivo, su peso meta, su nivel de "
                "actividad, restricciones o alergias). Se recalculan sus objetivos "
                "diarios automáticamente. Pasa solo los campos que cambian."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "current_weight_kg": {"type": "number"},
                    "height_cm": {"type": "number"},
                    "goal": {"type": "string", "enum": ["lose", "maintain", "gain"]},
                    "target_weight_kg": {"type": "number"},
                    "weekly_rate_kg": {"type": "number", "description": "kg por semana."},
                    "activity_level": {
                        "type": "string",
                        "enum": ["sedentary", "light", "moderate", "active", "very_active"],
                    },
                    "dietary_restrictions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista completa de restricciones/dieta (reemplaza la anterior).",
                    },
                    "allergies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista completa de alergias/intolerancias (reemplaza la anterior).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_diet_plan",
            "description": (
                "Devuelve la dieta recomendada del usuario: comidas propuestas y "
                "confirmadas con su día, tipo y hora. Úsala antes de proponer o "
                "modificar comidas para no duplicar, y cuando pregunte por su plan."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_diet_plan_item",
            "description": (
                "Propone una comida para el plan de dieta del usuario, en una FECHA "
                "concreta. Se guarda como PROPUESTA para que el usuario la confirme. "
                "Respeta sus gustos, restricciones y las notas «a tener en cuenta». "
                "Indica el título y la fecha: usa scheduled_date (YYYY-MM-DD) si la "
                "conoces, o weekday (0=Lunes … 6=Domingo) para el día más cercano. Si "
                "planificas varios días, llama a esta herramienta una vez por comida. "
                "No planifiques más de un mes vista."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Nombre de la comida, ej. 'Avena con fruta y nueces'.",
                    },
                    "scheduled_date": {
                        "type": "string",
                        "description": "Fecha concreta YYYY-MM-DD.",
                    },
                    "weekday": {
                        "type": "integer",
                        "description": "0=Lunes … 6=Domingo; se usa el día más cercano. Alternativa a scheduled_date.",
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "snack"],
                    },
                    "scheduled_time": {"type": "string", "description": "Hora HH:MM."},
                    "description": {"type": "string", "description": "Ingredientes o preparación."},
                    "calories": {"type": "number"},
                    "protein_g": {"type": "number"},
                    "carbs_g": {"type": "number"},
                    "fat_g": {"type": "number"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_diet_plan_item",
            "description": (
                "Modifica una comida del plan por su id (obtenlo con get_diet_plan). "
                "Úsala para confirmarla (status='confirmed') cuando el usuario la "
                "acepta, cambiar su contenido, fecha u hora."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"},
                    "status": {"type": "string", "enum": ["proposed", "confirmed"]},
                    "title": {"type": "string"},
                    "scheduled_date": {"type": "string", "description": "Fecha YYYY-MM-DD."},
                    "weekday": {"type": "integer", "description": "0=Lunes … 6=Domingo (día más cercano)."},
                    "meal_type": {"type": "string", "enum": ["breakfast", "lunch", "dinner", "snack"]},
                    "scheduled_time": {"type": "string", "description": "Hora HH:MM."},
                    "description": {"type": "string"},
                    "calories": {"type": "number"},
                    "protein_g": {"type": "number"},
                    "carbs_g": {"type": "number"},
                    "fat_g": {"type": "number"},
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_diet_plan_item",
            "description": "Elimina una comida del plan por su id (obtenlo con get_diet_plan).",
            "parameters": {
                "type": "object",
                "properties": {"item_id": {"type": "integer"}},
                "required": ["item_id"],
            },
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
        if name == "remember_preference":
            content = (arguments.get("content") or "").strip()
            if not content:
                return {"error": "missing 'content'"}
            note = await preferences.add_note(
                db,
                user,
                content=content,
                category=arguments.get("category") or "other",
                source="ai",
            )
            return {"saved": True, "note": preferences.note_to_dict(note)}
        if name == "update_profile":
            fields = {k: v for k, v in arguments.items() if v is not None}
            if not fields:
                return {"error": "no fields to update"}
            try:
                p = await profile_service.update_profile(db, user, **fields)
            except profile_service.ProfileValidationError as exc:
                return {"error": str(exc)}
            return {
                "updated": True,
                "targets": {
                    "calories": p.target_calories,
                    "protein_g": float(p.target_protein_g) if p.target_protein_g else None,
                    "carbs_g": float(p.target_carbs_g) if p.target_carbs_g else None,
                    "fat_g": float(p.target_fat_g) if p.target_fat_g else None,
                },
            }
        if name == "get_diet_plan":
            items = await diet_plan.list_items(db, user)
            return {"items": [diet_plan.item_to_dict(i) for i in items]}
        if name == "add_diet_plan_item":
            title = (arguments.get("title") or "").strip()
            if not title:
                return {"error": "missing 'title'"}
            item = await diet_plan.add_item(
                db,
                user,
                title=title,
                scheduled_date=arguments.get("scheduled_date"),
                weekday=arguments.get("weekday"),
                meal_type=arguments.get("meal_type"),
                scheduled_time=arguments.get("scheduled_time"),
                description=arguments.get("description"),
                calories=arguments.get("calories"),
                protein_g=arguments.get("protein_g"),
                carbs_g=arguments.get("carbs_g"),
                fat_g=arguments.get("fat_g"),
                status=DietItemStatus.PROPOSED,
                source="ai",
            )
            return {"added": True, "item": diet_plan.item_to_dict(item)}
        if name == "update_diet_plan_item":
            item_id = arguments.get("item_id")
            item = await diet_plan.get_item(db, user, item_id) if item_id else None
            if item is None:
                return {"error": "item no encontrado"}
            fields = {k: v for k, v in arguments.items() if k != "item_id"}
            item = await diet_plan.update_item(db, item, **fields)
            return {"updated": True, "item": diet_plan.item_to_dict(item)}
        if name == "remove_diet_plan_item":
            item_id = arguments.get("item_id")
            item = await diet_plan.get_item(db, user, item_id) if item_id else None
            if item is None:
                return {"error": "item no encontrado"}
            await diet_plan.delete_item(db, item)
            return {"removed": True}
        return {"error": f"unknown tool: {name}"}

    return execute
