import pytest
import os
import uuid
from datetime import datetime
import asyncio

from utils.logging import SessionLogger
import utils.http_client


SessionLogger.start_session(f"test_voice_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

from db import models, crud
from utils.config import settings
from services.voice_generation import generate_character_voice

# Skip the test if HUME_API_KEY is not available or invalid
if not settings.HUME_API_KEY or len(settings.HUME_API_KEY) < 10:
    pytest.skip("Valid HUME_API_KEY required for integration test", allow_module_level=True)

# db_session fixture is imported from conftest.py

@pytest.fixture
def test_text(db_session):
    """Create a test text entry in the database"""
    text_content = "This is a test text for voice generation integration testing."
    db_text = crud.create_text(db_session, content=text_content, title="Voice Test Text")
    yield db_text
    # No cleanup needed as we keep the data for inspection

@pytest.fixture
def test_character(db_session, test_text):
    """Create a test character in the database"""
    db_character = crud.create_character(
        db_session,
        text_id=test_text.id,
        name=f"TestCharacter_{uuid.uuid4().hex[:6]}",  # Add uniqueness to avoid name conflicts
        description="A character created for voice generation testing",
        intro_text="Hello, I am a test character. This is my voice which is being generated for testing purposes."
    )
    yield db_character
    # No cleanup needed as we keep the data for inspection

@pytest.mark.asyncio
async def test_generate_character_voice(db_session, test_text, test_character, monkeypatch):
    """
    Tests the voice generation pipeline using real Hume AI API calls.
    Requires a valid HUME_API_KEY environment variable.
    """
    print(f"Testing voice generation for character {test_character.name} (ID: {test_character.id})")
    
    # Assert initial state
    assert test_character.provider_id is None
    assert test_character.provider is None
    
    # Create a segment for the character to ensure voice generation
    segment = crud.create_text_segment(
        db_session,
        text_id=test_text.id,
        character_id=test_character.id,
        text="This is a test segment for voice generation.",
        sequence=1
    )
    
    # Generate voice using REAL API call - now with await
    voice_id = await generate_character_voice(
        db=db_session,
        character_id=test_character.id,
        character_name=test_character.name,
        character_description=test_character.description,
        character_intro_text=test_character.intro_text,
        text_id=test_text.id
    )
    
    # Refresh character from database
    db_session.refresh(test_character)
    
    # Verify voice was created and DB was updated
    assert voice_id is not None
    assert test_character.provider_id is not None
    assert test_character.provider == "HUME"
    assert test_character.provider_id == voice_id
    
    print(f"Successfully generated voice with ID: {voice_id}")

@pytest.mark.asyncio
async def test_generate_character_voice_no_segments(db_session, test_text, test_character):
    """
    Tests that voice generation is skipped for characters with no segments.
    """
    print(f"Testing voice generation skipped for character without segments")
    
    # Assert initial state
    assert test_character.provider_id is None
    assert test_character.provider is None
    
    # Generate voice for character without segments
    voice_id = await generate_character_voice(
        db=db_session,
        character_id=test_character.id,
        character_name=test_character.name,
        character_description=test_character.description,
        character_intro_text=test_character.intro_text,
        text_id=test_text.id
    )
    
    # Refresh character from database
    db_session.refresh(test_character)
    
    # Verify no voice was created
    assert voice_id is None
    assert test_character.provider_id is None
    assert test_character.provider is None
    
    print("Successfully skipped voice generation for character without segments") 