"""reminders (recurring notifications)

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-07-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    reminder_type = sa.Enum('MEAL', 'WATER', 'WEIGHT', 'CUSTOM', name='reminder_type')

    op.create_table(
        'reminders',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('type', reminder_type, nullable=False),
        sa.Column('message', sa.String(length=500), nullable=True),
        sa.Column('time', sa.Time(), nullable=False),
        sa.Column('days_of_week', postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('source', sa.String(length=16), nullable=False),
        sa.Column('last_sent_on', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reminders_user_id', 'reminders', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_reminders_user_id', table_name='reminders')
    op.drop_table('reminders')
    sa.Enum(name='reminder_type').drop(op.get_bind(), checkfirst=True)
