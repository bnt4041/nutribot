"""diet plan items use concrete dates instead of weekday

Revision ID: e2b3c4d5f6a7
Revises: d1a2b3c4e5f6
Create Date: 2026-07-02 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2b3c4d5f6a7'
down_revision: Union[str, None] = 'd1a2b3c4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('diet_plan_items', sa.Column('scheduled_date', sa.Date(), nullable=True))
    op.create_index(
        'ix_diet_plan_items_scheduled_date', 'diet_plan_items', ['scheduled_date'], unique=False
    )
    # Backfill: map the old weekday (0=Mon … 6=Sun) to the nearest upcoming date.
    # isodow: 1=Mon … 7=Sun, so plan weekday X corresponds to isodow X+1.
    op.execute(
        """
        UPDATE diet_plan_items
        SET scheduled_date = current_date
            + (((day_of_week + 1) - extract(isodow from current_date)::int + 7) % 7)
        WHERE day_of_week IS NOT NULL
        """
    )
    op.drop_column('diet_plan_items', 'day_of_week')


def downgrade() -> None:
    op.add_column(
        'diet_plan_items',
        sa.Column('day_of_week', sa.SmallInteger(), autoincrement=False, nullable=True),
    )
    # Reconstruct weekday from the date (isodow 1..7 -> plan 0..6).
    op.execute(
        """
        UPDATE diet_plan_items
        SET day_of_week = (extract(isodow from scheduled_date)::int - 1)
        WHERE scheduled_date IS NOT NULL
        """
    )
    op.drop_index('ix_diet_plan_items_scheduled_date', table_name='diet_plan_items')
    op.drop_column('diet_plan_items', 'scheduled_date')
