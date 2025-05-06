"""remove_persona_description_column

Revision ID: f9e214ad67d9
Revises: add_missing_columns
Create Date: 2025-05-06 20:34:56.315980

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision: str = 'f9e214ad67d9'
down_revision: Union[str, None] = 'add_missing_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support dropping columns directly, so we need to:
    # 1. Create a new table without the column
    # 2. Copy data from old table to new table
    # 3. Drop the old table
    # 4. Rename the new table to the original name
    
    # Create a new table without the persona_description column
    op.create_table('characters_new',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('text_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('provider_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('is_narrator', sa.Boolean(), nullable=True),
        sa.Column('speaking', sa.Boolean(), nullable=True),
        sa.Column('intro_text', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['text_id'], ['texts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Copy data from the old table to the new table
    op.execute(
        """
        INSERT INTO characters_new (id, text_id, name, description, provider_id, created_at, is_narrator, speaking, intro_text)
        SELECT id, text_id, name, description, provider_id, created_at, is_narrator, speaking, intro_text
        FROM characters;
        """
    )
    
    # Drop the old table
    op.drop_table('characters')
    
    # Rename the new table to the original name
    op.rename_table('characters_new', 'characters')


def downgrade() -> None:
    # Add the persona_description column back if needed
    op.add_column('characters', sa.Column('persona_description', sa.Text(), nullable=True))
