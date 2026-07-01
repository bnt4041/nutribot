"""Shared pytest fixtures."""

import pytest

from app.db.session import engine


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Dispose the async engine's pool after each test.

    pytest-asyncio runs each test in its own event loop; without disposing, the
    global engine would reuse pooled asyncpg connections bound to a closed loop.
    """
    yield
    await engine.dispose()
