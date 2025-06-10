"""add_sound_effects_table

Revision ID: d4d4f57bcdbb
Revises: e28196c69bb9
Create Date: 2025-06-09 15:28:59.363552

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4d4f57bcdbb'
down_revision: Union[str, None] = 'e28196c69bb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('sound_effects',
        sa.Column('effect_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('effect_name', sa.String(), nullable=False),
        sa.Column('text_id', sa.Integer(), nullable=False),
        sa.Column('segment_id', sa.Integer(), nullable=True),
        sa.Column('start_word', sa.String(), nullable=False),
        sa.Column('end_word', sa.String(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('audio_data_b64', sa.Text(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=True),
        sa.Column('end_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['segment_id'], ['text_segments.id'], ),
        sa.ForeignKeyConstraint(['text_id'], ['texts.id'], ),
        sa.PrimaryKeyConstraint('effect_id')
    )


def downgrade() -> None:
    op.drop_table('sound_effects')
