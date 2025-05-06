"""make_analyzed_field_not_nullable

Revision ID: 659ae9b1ca38
Revises: 505942455659
Create Date: 2025-05-06 22:33:44.294919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '659ae9b1ca38'
down_revision: Union[str, None] = '505942455659'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    pass


def downgrade() -> None:

    pass
