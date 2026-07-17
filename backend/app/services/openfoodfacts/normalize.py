"""Normalize Open Food Facts product payloads into a compact macro dict."""

from decimal import Decimal, InvalidOperation

from app.core.config import get_settings

settings = get_settings()


def product_url(barcode: str | None) -> str | None:
    """Canonical Open Food Facts product page URL for a barcode."""
    if not barcode:
        return None
    return f"{settings.off_base_url}/product/{barcode}"


def _to_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _kcal(nutriments: dict) -> Decimal | None:
    """Prefer kcal; fall back to converting kJ (energy_100g) to kcal."""
    kcal = _to_decimal(nutriments.get("energy-kcal_100g"))
    if kcal is not None:
        return kcal
    kj = _to_decimal(nutriments.get("energy_100g"))
    if kj is not None:
        return (kj / Decimal("4.184")).quantize(Decimal("0.01"))
    return None


def normalize_product(product: dict) -> dict | None:
    """Return a normalized food dict, or None if there is no usable name.

    Shape: {barcode, name, calories_100g, protein_100g, carbs_100g, fat_100g}.
    Numeric values are floats (JSON-friendly) or None when unknown.
    """
    name = (product.get("product_name") or "").strip()
    barcode = (product.get("code") or "").strip() or None
    if not name:
        return None

    nutriments = product.get("nutriments") or {}
    calories = _kcal(nutriments)
    protein = _to_decimal(nutriments.get("proteins_100g"))
    carbs = _to_decimal(nutriments.get("carbohydrates_100g"))
    fat = _to_decimal(nutriments.get("fat_100g"))
    fiber = _to_decimal(nutriments.get("fiber_100g"))

    image_url = product.get("image_front_url") or product.get("image_url") or None

    return {
        "barcode": barcode,
        "name": name,
        "calories_100g": float(calories) if calories is not None else None,
        "protein_100g": float(protein) if protein is not None else None,
        "carbs_100g": float(carbs) if carbs is not None else None,
        "fat_100g": float(fat) if fat is not None else None,
        "fiber_100g": float(fiber) if fiber is not None else None,
        "url": product_url(barcode),
        "image_url": image_url,
    }
