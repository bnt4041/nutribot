"""Low-level HTTP client for the Open Food Facts API."""

import httpx

from app.core.config import get_settings

settings = get_settings()

# Only request the fields we need, to keep responses small.
_FIELDS = "code,product_name,nutriments,image_front_url,image_url"


def _headers() -> dict[str, str]:
    return {"User-Agent": settings.off_user_agent}


async def fetch_product(barcode: str) -> dict | None:
    """Fetch a single product by barcode. Returns the raw product dict or None."""
    url = f"{settings.off_base_url}/api/v2/product/{barcode}"
    async with httpx.AsyncClient(timeout=20.0, headers=_headers()) as client:
        response = await client.get(url, params={"fields": _FIELDS})
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
    if data.get("status") == 0 or "product" not in data:
        return None
    return data["product"]


async def search_products(name: str, limit: int | None = None) -> list[dict]:
    """Search products by free text via Search-a-licious. Returns raw hits."""
    page_size = limit or settings.off_search_limit
    url = f"{settings.off_search_url}/search"
    params = {"q": name, "page_size": page_size, "fields": _FIELDS}
    async with httpx.AsyncClient(timeout=20.0, headers=_headers()) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    return data.get("hits", [])
