"""app settings singleton + inactivity nudge tracking on users

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('last_inactivity_nudge_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('inactivity_nudge_count', sa.Integer(), server_default='0', nullable=False))

    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('inactivity_reminder_enabled', sa.Boolean(), nullable=False),
        sa.Column('inactivity_reminder_days', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.execute(
        "INSERT INTO app_settings (id, inactivity_reminder_enabled, inactivity_reminder_days) "
        "VALUES (1, true, 3)"
    )


def downgrade() -> None:
    op.drop_table('app_settings')
    op.drop_column('users', 'inactivity_nudge_count')
    op.drop_column('users', 'last_inactivity_nudge_at')
