"""add_audio_timestamp_to_sound_effects

Revision ID: f84a7bee37ef
Revises: 33778a58baba
Create Date: 2025-01-30 01:46:53.050932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f84a7bee37ef'
down_revision: Union[str, None] = '33778a58baba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add audio_timestamp column to sound_effects table
    op.add_column('sound_effects', sa.Column('audio_timestamp', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove audio_timestamp column from sound_effects table
    op.drop_column('sound_effects', 'audio_timestamp')
