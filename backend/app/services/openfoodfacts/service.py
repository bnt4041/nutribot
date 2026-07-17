"""Cache-aware Open Food Facts lookups (barcode + name search)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.food_cache import FoodCache
from app.services.openfoodfacts import client
from app.services.openfoodfacts.normalize import normalize_product, product_url

settings = get_settings()


def _row_to_dict(row: FoodCache) -> dict:
    raw = row.raw_data or {}
    image_url = raw.get("image_front_url") or raw.get("image_url") or None
    return {
        "barcode": row.barcode,
        "name": row.product_name,
        "calories_100g": float(row.calories_100g) if row.calories_100g is not None else None,
        "protein_100g": float(row.protein_100g) if row.protein_100g is not None else None,
        "carbs_100g": float(row.carbs_100g) if row.carbs_100g is not None else None,
        "fat_100g": float(row.fat_100g) if row.fat_100g is not None else None,
        "fiber_100g": float(row.fiber_100g) if row.fiber_100g is not None else None,
        "url": product_url(row.barcode),
        "image_url": image_url,
    }


def _is_fresh(row: FoodCache) -> bool:
    ttl = timedelta(days=settings.off_cache_ttl_days)
    return datetime.now(timezone.utc) - row.fetched_at < ttl


async def _upsert(db: AsyncSession, normalized: dict, raw: dict) -> FoodCache:
    """Insert or refresh a cached product keyed by barcode."""
    barcode = normalized["barcode"]
    row = None
    if barcode is not None:
        result = await db.execute(select(FoodCache).where(FoodCache.barcode == barcode))
        row = result.scalar_one_or_none()

    if row is None:
        row = FoodCache(barcode=barcode)
        db.add(row)

    row.product_name = normalized["name"]
    row.calories_100g = normalized["calories_100g"]
    row.protein_100g = normalized["protein_100g"]
    row.carbs_100g = normalized["carbs_100g"]
    row.fat_100g = normalized["fat_100g"]
    row.fiber_100g = normalized["fiber_100g"]
    row.raw_data = raw
    row.fetched_at = datetime.now(timezone.utc)
    await db.flush()
    return row


async def get_by_barcode(db: AsyncSession, barcode: str) -> dict | None:
    """Return normalized product for a barcode, using cache when fresh."""
    barcode = barcode.strip()
    result = await db.execute(select(FoodCache).where(FoodCache.barcode == barcode))
    cached = result.scalar_one_or_none()
    if cached is not None and _is_fresh(cached):
        return _row_to_dict(cached)

    product = await client.fetch_product(barcode)
    if product is None:
        return None
    normalized = normalize_product(product)
    if normalized is None:
        return None
    await _upsert(db, normalized, product)
    return normalized


async def search(db: AsyncSession, name: str, limit: int | None = None) -> list[dict]:
    """Search products by name; cache those that carry a barcode."""
    products = await client.search_products(name, limit)
    results: list[dict] = []
    for product in products:
        normalized = normalize_product(product)
        if normalized is None:
            continue
        if normalized["barcode"] is not None:
            await _upsert(db, normalized, product)
        results.append(normalized)
    return results
