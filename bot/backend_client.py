"""HTTP client for talking to the NutriBot backend."""

import base64

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


async def send_photo_interaction(
    telegram_id: int,
    full_name: str | None,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    caption: str | None = None,
) -> dict:
    """POST a food photo to the backend for AI analysis.

    Returns the raw BotReply dict: {text, buttons, allow_free_text}.
    """
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    async with httpx.AsyncClient(
        timeout=max(settings.request_timeout, 120.0)  # vision calls may take longer
    ) as client:
        response = await client.post(
            f"{settings.backend_url}/api/v1/bot/message",
            json={
                "telegram_id": telegram_id,
                "full_name": full_name,
                "text": caption,
                "image_base64": image_b64,
                "image_mime": mime_type,
            },
        )
        response.raise_for_status()
        return response.json()


async def download_report(telegram_id: int) -> bytes:
    """Download the PDF nutrition report for a Telegram user.

    Returns the raw PDF bytes.
    """
    async with httpx.AsyncClient(
        timeout=max(settings.request_timeout, 30.0)
    ) as client:
        response = await client.get(
            f"{settings.backend_url}/api/v1/bot/report/{telegram_id}",
        )
        response.raise_for_status()
        return response.content
