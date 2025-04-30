"""Test fixtures for repository tests."""
import uuid
from typing import Dict, Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from narratix.infrastructure.database.engine import Base
from narratix.infrastructure.database.models import (
    TextContent as DBTextContent,
    Character as DBCharacter,
    Voice as DBVoice,
    NarrativeElement as DBNarrativeElement
)
from narratix.core.domain.entities.text_content import TextContent
from narratix.core.domain.entities.character import Character
from narratix.core.domain.entities.voice import Voice
from narratix.core.domain.entities.narrative_element import NarrativeElement


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(in_memory_db):
    """Create a new database session for testing."""
    Session = sessionmaker(bind=in_memory_db)
    session = Session()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_text_content() -> TextContent:
    """Create a sample TextContent entity for testing."""
    return TextContent(
        content="This is a sample text content for testing.",
        language="en",
        metadata={"source": "test"}
    )


@pytest.fixture
def sample_voice() -> Voice:
    """Create a sample Voice entity for testing."""
    return Voice(
        voice_id="test-voice-1",
        voice_name="Test Voice",
        provider="test-provider",
        gender="neutral",
        accent="standard",
        voice_description="A test voice for unit testing",
        pitch=1.0
    )


@pytest.fixture
def sample_character() -> Character:
    """Create a sample Character entity for testing."""
    return Character(
        name="Test Character",
        description="A character for testing purposes"
    )


@pytest.fixture
def sample_narrative_element(sample_text_content) -> NarrativeElement:
    """Create a sample NarrativeElement entity for testing."""
    # Ensure the text_content has an ID
    if not hasattr(sample_text_content, 'id'):
        sample_text_content.id = uuid.uuid4()
        
    return NarrativeElement(
        text_segment="This is a test narrative element.",
        start_offset=0,
        end_offset=32,
        element_type="narration",
        text_content_id=sample_text_content.id,
        acting_instructions="Read normally",
        speed=1.0,
        trailing_silence=0.5
    ) 