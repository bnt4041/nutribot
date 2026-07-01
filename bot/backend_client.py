"""HTTP client for talking to the NutriBot backend."""

import httpx

from config import get_settings

settings = get_settings()


async def request_login_code(telegram_id: int) -> dict:
    """Ask the backend for a one-time dashboard login code."""
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(
            f"{settings.backend_url}/api/v1/auth/request-code",
            json={"telegram_id": telegram_id},
        )
        response.raise_for_status()
        return response.json()


async def send_interaction(
    telegram_id: int,
    full_name: str | None,
    text: str | None = None,
    action: str | None = None,
) -> dict:
    """POST an interaction (text or button tap) to the unified bot endpoint.

    Returns the raw BotReply dict: {text, buttons, allow_free_text}.
    """
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(
            f"{settings.backend_url}/api/v1/bot/message",
            json={
                "telegram_id": telegram_id,
                "full_name": full_name,
                "text": text,
                "action": action,
            },
        )
        response.raise_for_status()
        return response.json()
