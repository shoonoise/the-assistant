"""merge migration heads

Revision ID: 30ef509e2503
Revises: 6e5d23f1c2ab, 9e55ed922174
Create Date: 2025-07-28 21:04:26.012206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30ef509e2503'
down_revision: Union[str, Sequence[str], None] = ('6e5d23f1c2ab', '9e55ed922174')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
