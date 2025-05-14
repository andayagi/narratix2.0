"""add_last_updated_to_characters_and_text_segments

Revision ID: 39db2f293ac7
Revises: 2d6b903a618a
Create Date: 2025-05-11 21:52:54.223281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39db2f293ac7'
down_revision: Union[str, None] = '2d6b903a618a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Characters table update
    # SQLite doesn't support adding a column with a function default, so we need to recreate tables
    
    # 1. Create characters_new with the schema we want
    op.execute('''
        CREATE TABLE characters_new (
            id INTEGER NOT NULL, 
            text_id INTEGER, 
            name VARCHAR NOT NULL, 
            description TEXT, 
            provider_id VARCHAR, 
            provider VARCHAR,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
            is_narrator BOOLEAN, 
            speaking BOOLEAN, 
            persona_description TEXT, 
            intro_text TEXT,
            last_updated DATETIME DEFAULT (CURRENT_TIMESTAMP),
            PRIMARY KEY (id),
            FOREIGN KEY(text_id) REFERENCES texts (id)
        )
    ''')
    
    # 2. Copy data from old table to new table - use current timestamp for last_updated
    op.execute('''
        INSERT INTO characters_new 
        SELECT id, text_id, name, description, provider_id, provider, created_at, 
               is_narrator, speaking, persona_description, intro_text, CURRENT_TIMESTAMP 
        FROM characters
    ''')
    
    # 3. Drop old table and rename new one
    op.execute('DROP TABLE characters')
    op.execute('ALTER TABLE characters_new RENAME TO characters')
    
    # 4. Create a trigger for automatic update of last_updated on characters table
    op.execute('''
        CREATE TRIGGER update_characters_last_updated
        AFTER UPDATE ON characters
        FOR EACH ROW
        BEGIN
            UPDATE characters SET last_updated = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
    ''')
    
    # Text segments table update
    # 1. Create text_segments_new with the schema we want
    op.execute('''
        CREATE TABLE text_segments_new (
            id INTEGER NOT NULL, 
            text_id INTEGER, 
            character_id INTEGER, 
            text TEXT NOT NULL, 
            sequence INTEGER NOT NULL, 
            audio_file VARCHAR, 
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
            description TEXT, 
            speed FLOAT, 
            trailing_silence FLOAT,
            last_updated DATETIME DEFAULT (CURRENT_TIMESTAMP),
            PRIMARY KEY (id),
            FOREIGN KEY(text_id) REFERENCES texts (id),
            FOREIGN KEY(character_id) REFERENCES characters (id)
        )
    ''')
    
    # 2. Copy data from old table to new table - use current timestamp for last_updated
    op.execute('''
        INSERT INTO text_segments_new 
        SELECT id, text_id, character_id, text, sequence, audio_file, created_at, 
               description, speed, trailing_silence, CURRENT_TIMESTAMP 
        FROM text_segments
    ''')
    
    # 3. Drop old table and rename new one
    op.execute('DROP TABLE text_segments')
    op.execute('ALTER TABLE text_segments_new RENAME TO text_segments')
    
    # 4. Create a trigger for automatic update of last_updated on text_segments table
    op.execute('''
        CREATE TRIGGER update_text_segments_last_updated
        AFTER UPDATE ON text_segments
        FOR EACH ROW
        BEGIN
            UPDATE text_segments SET last_updated = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
    ''')


def downgrade() -> None:
    # Drop triggers first
    op.execute('DROP TRIGGER IF EXISTS update_characters_last_updated')
    op.execute('DROP TRIGGER IF EXISTS update_text_segments_last_updated')
    
    # Characters table downgrade
    # 1. Create characters_new without last_updated
    op.execute('''
        CREATE TABLE characters_new (
            id INTEGER NOT NULL, 
            text_id INTEGER, 
            name VARCHAR NOT NULL, 
            description TEXT, 
            provider_id VARCHAR, 
            provider VARCHAR,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
            is_narrator BOOLEAN, 
            speaking BOOLEAN, 
            persona_description TEXT, 
            intro_text TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY(text_id) REFERENCES texts (id)
        )
    ''')
    
    # 2. Copy data from current table to new table (excluding last_updated)
    op.execute('''
        INSERT INTO characters_new 
        SELECT id, text_id, name, description, provider_id, provider, created_at, 
               is_narrator, speaking, persona_description, intro_text
        FROM characters
    ''')
    
    # 3. Drop current table and rename new one
    op.execute('DROP TABLE characters')
    op.execute('ALTER TABLE characters_new RENAME TO characters')
    
    # Text segments table downgrade
    # 1. Create text_segments_new without last_updated
    op.execute('''
        CREATE TABLE text_segments_new (
            id INTEGER NOT NULL, 
            text_id INTEGER, 
            character_id INTEGER, 
            text TEXT NOT NULL, 
            sequence INTEGER NOT NULL, 
            audio_file VARCHAR, 
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
            description TEXT, 
            speed FLOAT, 
            trailing_silence FLOAT,
            PRIMARY KEY (id),
            FOREIGN KEY(text_id) REFERENCES texts (id),
            FOREIGN KEY(character_id) REFERENCES characters (id)
        )
    ''')
    
    # 2. Copy data from current table to new table (excluding last_updated)
    op.execute('''
        INSERT INTO text_segments_new 
        SELECT id, text_id, character_id, text, sequence, audio_file, created_at, 
               description, speed, trailing_silence
        FROM text_segments
    ''')
    
    # 3. Drop current table and rename new one
    op.execute('DROP TABLE text_segments')
    op.execute('ALTER TABLE text_segments_new RENAME TO text_segments')
