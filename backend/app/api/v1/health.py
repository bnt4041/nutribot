"""Health check endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health() -> dict[str, str]:
    """Liveness probe: confirms the API process is up."""
    return {"status": "ok"}


@router.get("/db")
async def health_db(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Readiness probe: verifies DB connectivity and that pgvector is available."""
    try:
        await db.execute(text("SELECT 1"))
        await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await db.commit()
    except Exception as exc:  # noqa: BLE001 - surface any DB failure as 503
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"database unavailable: {exc}",
        ) from exc

    return {"status": "ok", "database": "ok", "pgvector": "ok"}
