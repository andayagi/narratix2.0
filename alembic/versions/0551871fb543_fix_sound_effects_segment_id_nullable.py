"""fix_sound_effects_segment_id_nullable

Revision ID: 0551871fb543
Revises: 59660be62070
Create Date: 2025-06-10 12:20:00.147387

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0551871fb543'
down_revision: Union[str, None] = '59660be62070'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
    # First, create a temporary table with the correct schema
    op.execute("""
        CREATE TABLE sound_effects_temp (
            effect_id INTEGER NOT NULL, 
            effect_name VARCHAR NOT NULL, 
            text_id INTEGER NOT NULL, 
            segment_id INTEGER,  -- Now nullable
            start_word VARCHAR NOT NULL, 
            end_word VARCHAR NOT NULL, 
            prompt TEXT NOT NULL, 
            audio_data_b64 TEXT NOT NULL, 
            start_time FLOAT, 
            end_time FLOAT, 
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            start_word_position INTEGER,
            end_word_position INTEGER,
            PRIMARY KEY (effect_id), 
            FOREIGN KEY(segment_id) REFERENCES text_segments (id), 
            FOREIGN KEY(text_id) REFERENCES texts (id)
        )
    """)
    
    # Copy data from the old table to the new one
    op.execute("""
        INSERT INTO sound_effects_temp 
        SELECT * FROM sound_effects
    """)
    
    # Drop the old table and rename the new one
    op.execute("DROP TABLE sound_effects")
    op.execute("ALTER TABLE sound_effects_temp RENAME TO sound_effects")


def downgrade() -> None:
    # Reverse operation - make segment_id NOT NULL again
    op.execute("""
        CREATE TABLE sound_effects_temp (
            effect_id INTEGER NOT NULL, 
            effect_name VARCHAR NOT NULL, 
            text_id INTEGER NOT NULL, 
            segment_id INTEGER NOT NULL,  -- Back to NOT NULL
            start_word VARCHAR NOT NULL, 
            end_word VARCHAR NOT NULL, 
            prompt TEXT NOT NULL, 
            audio_data_b64 TEXT NOT NULL, 
            start_time FLOAT, 
            end_time FLOAT, 
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            start_word_position INTEGER,
            end_word_position INTEGER,
            PRIMARY KEY (effect_id), 
            FOREIGN KEY(segment_id) REFERENCES text_segments (id), 
            FOREIGN KEY(text_id) REFERENCES texts (id)
        )
    """)
    
    op.execute("""
        INSERT INTO sound_effects_temp 
        SELECT * FROM sound_effects WHERE segment_id IS NOT NULL
    """)
    
    op.execute("DROP TABLE sound_effects")
    op.execute("ALTER TABLE sound_effects_temp RENAME TO sound_effects")
