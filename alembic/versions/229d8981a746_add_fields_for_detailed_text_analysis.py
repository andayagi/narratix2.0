"""Add fields for detailed text analysis

Revision ID: 229d8981a746
Revises: aaada83994fa
Create Date: 2025-05-05 00:59:25.908155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# Remove unused import
# from sqlalchemy.dialects import postgresql 

# revision identifiers, used by Alembic.
revision: str = '229d8981a746'
down_revision: Union[str, None] = 'aaada83994fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Corrected Alembic commands
    # Add new columns to characters table
    op.add_column('characters', sa.Column('is_narrator', sa.Boolean(), nullable=True))
    op.add_column('characters', sa.Column('speaking', sa.Boolean(), nullable=True))
    op.add_column('characters', sa.Column('persona_description', sa.Text(), nullable=True))
    op.add_column('characters', sa.Column('intro_text', sa.Text(), nullable=True))

    # Rename content column and add new columns to text_segments table
    op.alter_column('text_segments', 'content', new_column_name='text', existing_type=sa.Text(), nullable=False)
    op.add_column('text_segments', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('text_segments', sa.Column('speed', sa.Float(), nullable=True))
    op.add_column('text_segments', sa.Column('trailing_silence', sa.Float(), nullable=True))
    # ### end corrected Alembic commands ###


def downgrade() -> None:
    # Corrected Alembic commands for downgrade
    # Remove columns from text_segments table and rename text back to content
    op.drop_column('text_segments', 'trailing_silence')
    op.drop_column('text_segments', 'speed')
    op.drop_column('text_segments', 'description')
    op.alter_column('text_segments', 'text', new_column_name='content', existing_type=sa.Text(), nullable=False)

    # Remove new columns from characters table
    op.drop_column('characters', 'intro_text')
    op.drop_column('characters', 'persona_description')
    op.drop_column('characters', 'speaking')
    op.drop_column('characters', 'is_narrator')
    # ### end corrected Alembic commands ###
