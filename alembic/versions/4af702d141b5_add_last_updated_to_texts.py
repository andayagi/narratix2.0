"""add_last_updated_to_texts

Revision ID: 4af702d141b5
Revises: b7d755b443e9
Create Date: 2025-05-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4af702d141b5'
down_revision: Union[str, None] = 'b7d755b443e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support adding a column with a function default
    # Need to recreate the table
    
    # Create new table with the schema we want
    op.execute('CREATE TABLE texts_new (id INTEGER NOT NULL, content TEXT NOT NULL, title VARCHAR, created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), analyzed BOOLEAN NOT NULL DEFAULT False, last_updated DATETIME DEFAULT (CURRENT_TIMESTAMP), PRIMARY KEY (id))')
    
    # Copy data from old table to new table - use current timestamp for last_updated
    op.execute('INSERT INTO texts_new SELECT id, content, title, created_at, analyzed, CURRENT_TIMESTAMP FROM texts')
    
    # Drop old table and rename new one
    op.execute('DROP TABLE texts')
    op.execute('ALTER TABLE texts_new RENAME TO texts')
    
    # Create a trigger to automatically update the last_updated field
    op.execute('''
        CREATE TRIGGER update_texts_last_updated
        AFTER UPDATE ON texts
        FOR EACH ROW
        BEGIN
            UPDATE texts SET last_updated = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
    ''')


def downgrade() -> None:
    # Drop the trigger first
    op.execute('DROP TRIGGER IF EXISTS update_texts_last_updated')
    
    # Similar process but reversing the changes
    op.execute('CREATE TABLE texts_new (id INTEGER NOT NULL, content TEXT NOT NULL, title VARCHAR, created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), analyzed BOOLEAN NOT NULL DEFAULT False, PRIMARY KEY (id))')
    op.execute('INSERT INTO texts_new SELECT id, content, title, created_at, analyzed FROM texts')
    op.execute('DROP TABLE texts')
    op.execute('ALTER TABLE texts_new RENAME TO texts')
