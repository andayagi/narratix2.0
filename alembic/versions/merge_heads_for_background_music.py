"""merge_heads_for_background_music

Revision ID: merge_heads_background_music
Revises: add_background_music_prompt, d8c7d90a1e42
Create Date: 2023-10-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_heads_background_music'
down_revision = None
# Multiple parents - merging heads
branch_labels = None
depends_on = None

# Branch 1: The background music migration
branch_1 = 'add_background_music_prompt'
# Branch 2: The existing head from the DB
branch_2 = 'd8c7d90a1e42'

def upgrade():
    pass


def downgrade():
    pass 