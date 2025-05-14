"""fix_timestamp_triggers

Revision ID: d8c7d90a1e42
Revises: 39db2f293ac7
Create Date: 2025-05-18 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = 'd8c7d90a1e42'
down_revision: Union[str, None] = '39db2f293ac7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update existing timestamps to fix the issue
    current_time = datetime.now().isoformat()
    
    # First, update all last_updated timestamps in all tables to the current time
    op.execute(f"UPDATE texts SET last_updated = '{current_time}'")
    op.execute(f"UPDATE characters SET last_updated = '{current_time}'")
    op.execute(f"UPDATE text_segments SET last_updated = '{current_time}'")
    
    # Ensure all triggers are dropped if they exist
    op.execute('DROP TRIGGER IF EXISTS update_texts_last_updated')
    op.execute('DROP TRIGGER IF EXISTS update_characters_last_updated')
    op.execute('DROP TRIGGER IF EXISTS update_text_segments_last_updated')
    
    # Recreate all the triggers to ensure last_updated is updated properly in future
    # Trigger for texts
    op.execute('''
        CREATE TRIGGER update_texts_last_updated
        AFTER UPDATE ON texts
        FOR EACH ROW
        BEGIN
            UPDATE texts SET last_updated = datetime('now', 'localtime') WHERE id = NEW.id;
        END;
    ''')
    
    # Trigger for characters
    op.execute('''
        CREATE TRIGGER update_characters_last_updated
        AFTER UPDATE ON characters
        FOR EACH ROW
        BEGIN
            UPDATE characters SET last_updated = datetime('now', 'localtime') WHERE id = NEW.id;
        END;
    ''')
    
    # Trigger for text_segments
    op.execute('''
        CREATE TRIGGER update_text_segments_last_updated
        AFTER UPDATE ON text_segments
        FOR EACH ROW
        BEGIN
            UPDATE text_segments SET last_updated = datetime('now', 'localtime') WHERE id = NEW.id;
        END;
    ''')


def downgrade() -> None:
    # Drop the triggers
    op.execute('DROP TRIGGER IF EXISTS update_texts_last_updated')
    op.execute('DROP TRIGGER IF EXISTS update_characters_last_updated')
    op.execute('DROP TRIGGER IF EXISTS update_text_segments_last_updated') 