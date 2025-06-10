"""add_rank_to_sound_effects

Revision ID: 33778a58baba
Revises: d092f77921f9
Create Date: 2025-06-10 22:13:34.428684

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33778a58baba'
down_revision: Union[str, None] = 'd092f77921f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add rank column to sound_effects table
    op.add_column('sound_effects', sa.Column('rank', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove rank column from sound_effects table
    op.drop_column('sound_effects', 'rank')
