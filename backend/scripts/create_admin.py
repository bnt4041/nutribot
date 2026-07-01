"""Create or update an admin user (email + password).

Usage (inside the backend container):
    uv run python scripts/create_admin.py <email> <password> [full_name]
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import async_session_factory
from app.models.enums import UserRole
from app.models.user import User


async def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: create_admin.py <email> <password> [full_name]")
        sys.exit(1)
    email, password = sys.argv[1], sys.argv[2]
    full_name = sys.argv[3] if len(sys.argv) > 3 else "Admin"

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(email=email, full_name=full_name)
            session.add(user)
        user.role = UserRole.ADMIN
        user.is_active = True
        user.password_hash = hash_password(password)
        await session.commit()
        await session.refresh(user)
        print(f"Admin ready: id={user.id} email={user.email}")


if __name__ == "__main__":
    asyncio.run(main())
