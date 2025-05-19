"""merge_heads_for_audio_data

Revision ID: 9f70f2e17485
Revises: add_background_music_prompt, d8c7d90a1e42, merge_heads_background_music
Create Date: 2025-05-14 23:24:17.238718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f70f2e17485'
down_revision: Union[str, None] = ('add_background_music_prompt', 'd8c7d90a1e42', 'merge_heads_background_music')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
