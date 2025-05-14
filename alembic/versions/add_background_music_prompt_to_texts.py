"""add_background_music_prompt_to_texts

Revision ID: add_background_music_prompt
Revises: 4af702d141b5
Create Date: 2023-10-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_background_music_prompt'
down_revision = '4af702d141b5'
branch_labels = None
depends_on = None


def upgrade():
    # Add background_music_prompt column to texts table
    op.add_column('texts', sa.Column('background_music_prompt', sa.Text(), nullable=True))


def downgrade():
    # Remove background_music_prompt column from texts table
    op.drop_column('texts', 'background_music_prompt') 