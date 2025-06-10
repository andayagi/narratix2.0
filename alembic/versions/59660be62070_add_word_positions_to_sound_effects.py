"""add_word_positions_to_sound_effects

Revision ID: 59660be62070
Revises: d4d4f57bcdbb
Create Date: 2025-06-09 16:04:57.337970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59660be62070'
down_revision: Union[str, None] = 'd4d4f57bcdbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add word position columns to sound_effects table
    op.add_column('sound_effects', sa.Column('start_word_position', sa.Integer(), nullable=True))
    op.add_column('sound_effects', sa.Column('end_word_position', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove word position columns
    op.drop_column('sound_effects', 'end_word_position')
    op.drop_column('sound_effects', 'start_word_position')
