"""add_bg_audio_timestamp_to_texts

Revision ID: 9b2b768fdadd
Revises: f84a7bee37ef
Create Date: 2025-07-01 16:24:16.869854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b2b768fdadd'
down_revision: Union[str, None] = 'f84a7bee37ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add bg_audio_timestamp column to texts table
    op.add_column('texts', sa.Column('bg_audio_timestamp', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove bg_audio_timestamp column from texts table
    op.drop_column('texts', 'bg_audio_timestamp')
