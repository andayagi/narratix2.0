"""add_last_updated_to_texts

Revision ID: b8413c0d5508
Revises: b7d755b443e9
Create Date: 2025-05-06 23:36:52.636324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8413c0d5508'
down_revision: Union[str, None] = 'b7d755b443e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
