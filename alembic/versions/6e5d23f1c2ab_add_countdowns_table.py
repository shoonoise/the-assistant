"""Add countdowns table

Revision ID: 6e5d23f1c2ab
Revises: 9b31f1c67e3a
Create Date: 2025-07-29 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '6e5d23f1c2ab'
down_revision: str | Sequence[str] | None = '9b31f1c67e3a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'countdowns',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )


def downgrade() -> None:
    op.drop_table('countdowns')
