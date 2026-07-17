"""add 'news' value to reminder_type enum

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE reminder_type ADD VALUE IF NOT EXISTS 'NEWS'")


def downgrade() -> None:
    # Postgres has no DROP VALUE; removing it would require recreating the
    # enum type and remapping every column that uses it. Not supported.
    raise NotImplementedError("Cannot remove a value from reminder_type enum")
