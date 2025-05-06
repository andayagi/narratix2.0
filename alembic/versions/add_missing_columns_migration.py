"""Add missing columns to text_segments

Revision ID: add_missing_columns
Revises: 229d8981a746
Create Date: 2025-05-06 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_missing_columns'
down_revision: Union[str, None] = '229d8981a746'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if columns exist before adding them
    with op.batch_alter_table('text_segments') as batch_op:
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('speed', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('trailing_silence', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove columns from text_segments table
    with op.batch_alter_table('text_segments') as batch_op:
        batch_op.drop_column('trailing_silence')
        batch_op.drop_column('speed')
        batch_op.drop_column('description') 