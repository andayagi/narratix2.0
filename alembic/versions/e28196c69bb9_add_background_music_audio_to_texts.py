"""add_background_music_audio_to_texts

Revision ID: e28196c69bb9
Revises: 117af58c89f8
Create Date: 2025-05-18 12:43:14.120832

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e28196c69bb9'
down_revision: Union[str, None] = '117af58c89f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('texts', sa.Column('background_music_audio_b64', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('texts', 'background_music_audio_b64')
