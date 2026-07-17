"""add fiber tracking and water intake logging

Revision ID: f3a4b5c6d7e8
Revises: e2b3c4d5f6a7
Create Date: 2026-07-03 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, None] = 'e2b3c4d5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('food_cache', sa.Column('fiber_100g', sa.Numeric(8, 2), nullable=True))
    op.add_column('meal_logs', sa.Column('fiber_g', sa.Numeric(8, 2), nullable=True))
    op.add_column('diet_plan_items', sa.Column('fiber_g', sa.Numeric(8, 2), nullable=True))
    op.add_column('nutrition_profiles', sa.Column('target_fiber_g', sa.Numeric(6, 2), nullable=True))
    op.add_column('nutrition_profiles', sa.Column('target_water_ml', sa.Integer(), nullable=True))

    op.create_table(
        'water_logs',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column(
            'user_id', sa.BigInteger(),
            sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column('amount_ml', sa.Numeric(7, 2), nullable=False),
        sa.Column(
            'logged_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.create_index('ix_water_logs_user_id', 'water_logs', ['user_id'])
    op.create_index('ix_water_logs_logged_at', 'water_logs', ['logged_at'])


def downgrade() -> None:
    op.drop_index('ix_water_logs_logged_at', table_name='water_logs')
    op.drop_index('ix_water_logs_user_id', table_name='water_logs')
    op.drop_table('water_logs')

    op.drop_column('nutrition_profiles', 'target_water_ml')
    op.drop_column('nutrition_profiles', 'target_fiber_g')
    op.drop_column('diet_plan_items', 'fiber_g')
    op.drop_column('meal_logs', 'fiber_g')
    op.drop_column('food_cache', 'fiber_100g')
