"""Tests for Open Food Facts normalization and caching."""

import pytest

from app.db.session import async_session_factory
from app.models.food_cache import FoodCache
from app.services.openfoodfacts import service as off_service
from app.services.openfoodfacts.normalize import normalize_product


def test_normalize_prefers_kcal():
    product = {
        "code": "123",
        "product_name": "Yogur",
        "nutriments": {
            "energy-kcal_100g": 59,
            "proteins_100g": 10,
            "carbohydrates_100g": 3.6,
            "fat_100g": 0.4,
        },
    }
    result = normalize_product(product)
    assert result["barcode"] == "123"
    assert result["name"] == "Yogur"
    assert result["calories_100g"] == 59
    assert result["protein_100g"] == 10


def test_normalize_converts_kj_when_no_kcal():
    product = {
        "code": "456",
        "product_name": "Galleta",
        "nutriments": {"energy_100g": 2092},  # kJ -> ~500 kcal
    }
    result = normalize_product(product)
    assert result["calories_100g"] == pytest.approx(500, abs=1)


def test_normalize_rejects_nameless_product():
    assert normalize_product({"code": "789", "product_name": ""}) is None


@pytest.mark.asyncio
async def test_get_by_barcode_uses_cache_without_network(monkeypatch):
    """A fresh cache row must be returned without calling the OFF client."""

    async def _boom(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("network should not be hit on a cache hit")

    monkeypatch.setattr(off_service.client, "fetch_product", _boom)

    async with async_session_factory() as session:
        try:
            session.add(
                FoodCache(
                    barcode="CACHETEST-1",
                    product_name="Producto cacheado",
                    calories_100g=100,
                    protein_100g=5,
                )
            )
            await session.flush()

            result = await off_service.get_by_barcode(session, "CACHETEST-1")
            assert result is not None
            assert result["name"] == "Producto cacheado"
            assert result["calories_100g"] == 100
        finally:
            await session.rollback()
