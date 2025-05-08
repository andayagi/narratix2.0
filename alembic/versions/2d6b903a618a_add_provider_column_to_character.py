"""add_provider_column_to_character

Revision ID: 2d6b903a618a
Revises: fd2dd0405c0d
Create Date: 2025-05-07 10:17:45.101673

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d6b903a618a'
down_revision: Union[str, None] = 'fd2dd0405c0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('characters', sa.Column('provider', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('characters', 'provider')
