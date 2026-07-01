"""Client for the Text Embeddings Inference (bge-m3) service."""

import httpx

from app.core.config import get_settings

settings = get_settings()


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return normalized embeddings for a list of texts."""
    if not texts:
        return []
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.embeddings_url}/embed",
            json={"inputs": texts, "normalize": True},
        )
        response.raise_for_status()
        return response.json()


async def embed_query(text: str) -> list[float]:
    """Return the embedding for a single query string."""
    vectors = await embed_texts([text])
    return vectors[0]
