"""set_analyzed_default_value

Revision ID: b7d755b443e9
Revises: 659ae9b1ca38
Create Date: 2025-05-06 22:39:43.720440

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d755b443e9'
down_revision: Union[str, None] = '659ae9b1ca38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    
    op.execute('CREATE TABLE texts_new (id INTEGER NOT NULL, content TEXT NOT NULL, title VARCHAR, created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), analyzed BOOLEAN NOT NULL DEFAULT False, PRIMARY KEY (id))')
    
    op.execute('INSERT INTO texts_new SELECT id, content, title, created_at, COALESCE(analyzed, False) FROM texts')
    
    # Drop old table and rename new one
    op.execute('DROP TABLE texts')
    op.execute('ALTER TABLE texts_new RENAME TO texts')


def downgrade() -> None:
    # Similar process but reversing the changes
    op.execute('CREATE TABLE texts_new (id INTEGER NOT NULL, content TEXT NOT NULL, title VARCHAR, created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), analyzed BOOLEAN, PRIMARY KEY (id))')
    op.execute('INSERT INTO texts_new SELECT id, content, title, created_at, analyzed FROM texts')
    op.execute('DROP TABLE texts')
    op.execute('ALTER TABLE texts_new RENAME TO texts')
