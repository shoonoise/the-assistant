"""Add tasks table

Revision ID: 9b31f1c67e3a
Revises: 7cc1a1bbfedb
Create Date: 2025-07-28 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '9b31f1c67e3a'
down_revision: str | Sequence[str] | None = '7cc1a1bbfedb'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('raw_instruction', sa.Text(), nullable=False),
        sa.Column('schedule', sa.String(), nullable=False),
        sa.Column('instruction', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )


def downgrade() -> None:
    op.drop_table('tasks')
