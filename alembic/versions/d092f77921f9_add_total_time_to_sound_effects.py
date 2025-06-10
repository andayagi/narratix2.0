"""add_total_time_to_sound_effects

Revision ID: d092f77921f9
Revises: 82874e620bcc
Create Date: 2025-06-10 19:27:12.692676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd092f77921f9'
down_revision: Union[str, None] = '82874e620bcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add total_time column to sound_effects table
    op.add_column('sound_effects', sa.Column('total_time', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove total_time column from sound_effects table
    op.drop_column('sound_effects', 'total_time')
