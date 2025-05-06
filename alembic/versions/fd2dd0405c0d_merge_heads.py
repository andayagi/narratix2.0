"""merge heads

Revision ID: fd2dd0405c0d
Revises: b8413c0d5508, 4af702d141b5
Create Date: 2025-05-06 23:41:56.010534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd2dd0405c0d'
down_revision: Union[str, None] = ('b8413c0d5508', '4af702d141b5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
