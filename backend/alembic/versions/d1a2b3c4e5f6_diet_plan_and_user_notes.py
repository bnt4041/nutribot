"""diet plan items and user notes

Revision ID: d1a2b3c4e5f6
Revises: 4ac58f53933c
Create Date: 2026-07-02 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd1a2b3c4e5f6'
down_revision: Union[str, None] = '4ac58f53933c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Reuse the existing meal_type enum; don't recreate it.
    meal_type = postgresql.ENUM(
        'BREAKFAST', 'LUNCH', 'DINNER', 'SNACK', name='meal_type', create_type=False
    )
    diet_item_status = sa.Enum('PROPOSED', 'CONFIRMED', name='diet_item_status')
    note_category = sa.Enum(
        'DISLIKE', 'LIKE', 'MEDICAL', 'HABIT', 'OTHER', name='note_category'
    )

    op.create_table(
        'diet_plan_items',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('day_of_week', sa.SmallInteger(), nullable=True),
        sa.Column('meal_type', meal_type, nullable=True),
        sa.Column('scheduled_time', sa.Time(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=2000), nullable=True),
        sa.Column('calories', sa.Numeric(8, 2), nullable=True),
        sa.Column('protein_g', sa.Numeric(8, 2), nullable=True),
        sa.Column('carbs_g', sa.Numeric(8, 2), nullable=True),
        sa.Column('fat_g', sa.Numeric(8, 2), nullable=True),
        sa.Column('status', diet_item_status, nullable=False),
        sa.Column('source', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_diet_plan_items_user_id', 'diet_plan_items', ['user_id'], unique=False)

    op.create_table(
        'user_notes',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('category', note_category, nullable=False),
        sa.Column('content', sa.String(length=1000), nullable=False),
        sa.Column('source', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_notes_user_id', 'user_notes', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_notes_user_id', table_name='user_notes')
    op.drop_table('user_notes')
    op.drop_index('ix_diet_plan_items_user_id', table_name='diet_plan_items')
    op.drop_table('diet_plan_items')
    sa.Enum(name='note_category').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='diet_item_status').drop(op.get_bind(), checkfirst=True)
