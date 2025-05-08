import pytest
import os
import uuid
from datetime import datetime

from utils.logging import SessionLogger
SessionLogger.start_session(f"test_audio_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

from db import models, crud
from utils.config import settings
from services.audio_generation import generate_text_audio

# Skip the test if HUME_API_KEY is not available or invalid
if not settings.HUME_API_KEY or len(settings.HUME_API_KEY) < 10:
    pytest.skip("Valid HUME_API_KEY required for integration test", allow_module_level=True)

# db_session fixture is imported from conftest.py

# Voice IDs
MAN_VOICE_ID = "f0f92a3c-a181-4ee3-abeb-63ed8eacf898"
WOMAN_VOICE_ID = "f6f2cc66-2e13-46ce-88c8-c049cf6e8c64"  

@pytest.fixture
def test_text(db_session):
    """Create a test text entry in the database"""
    text_content = "This is a test text for audio generation integration testing."
    db_text = crud.create_text(db_session, content=text_content, title="Audio Test Text")
    yield db_text
    # No cleanup needed as we keep the data for inspection

@pytest.fixture
def test_male_character(db_session, test_text):
    """Create a test male character in the database with predefined voice ID"""
    db_character = crud.create_character(
        db_session,
        text_id=test_text.id,
        name=f"MaleCharacter_{uuid.uuid4().hex[:6]}",
        description="A male character for audio generation testing",
        intro_text="Hello, I am a male test character.",
        provider_id=MAN_VOICE_ID
    )
    yield db_character

@pytest.fixture
def test_female_character(db_session, test_text):
    """Create a test female character in the database with predefined voice ID"""
    db_character = crud.create_character(
        db_session,
        text_id=test_text.id,
        name=f"FemaleCharacter_{uuid.uuid4().hex[:6]}",
        description="A female character for audio generation testing",
        intro_text="Hello, I am a female test character.",
        provider_id=WOMAN_VOICE_ID
    )

    yield db_character

@pytest.fixture
def segments(db_session, test_text, test_male_character, test_female_character):
    """Create test segments for audio generation"""
    segments = []
    
    # Create segments for male character
    male_segment = crud.create_text_segment(
        db_session,
        text_id=test_text.id,
        character_id=test_male_character.id,
        text="This is the male character speaking for the audio test.",
        sequence=1,
        description="Calm and clear voice",
        speed=1.0,
        trailing_silence=0.5
    )
    segments.append(male_segment)
    
    # Create segments for female character
    female_segment = crud.create_text_segment(
        db_session,
        text_id=test_text.id,
        character_id=test_female_character.id,
        text="And this is the female character responding in the audio test.",
        sequence=2,
        description="Enthusiastic tone",
        speed=1.1,
        trailing_silence=0.3
    )
    segments.append(female_segment)
    
    # Add a final male segment
    final_segment = crud.create_text_segment(
        db_session,
        text_id=test_text.id,
        character_id=test_male_character.id,
        text="Thank you for listening to our test audio.",
        sequence=3,
        description="Thankful tone",
        speed=0.9,
        trailing_silence=1.0
    )
    segments.append(final_segment)
    
    yield segments

@pytest.mark.integration
def test_generate_text_audio(db_session, test_text, test_male_character, test_female_character, segments):
    """
    Tests the audio generation pipeline using real Hume AI API calls.
    Uses predefined character voices instead of generating new ones.
    """
    print(f"Testing audio generation for text {test_text.id} with {len(segments)} segments")
    
    # Verify initial state
    for segment in segments:
        assert segment.audio_file is None
    
    # Generate audio using REAL API call
    audio_file_path = generate_text_audio(db=db_session, text_id=test_text.id)
    
    # Verify audio was generated
    assert audio_file_path is not None
    assert os.path.exists(audio_file_path)
    
    # Refresh segments from database
    for segment in segments:
        db_session.refresh(segment)
        assert segment.audio_file is not None
        assert segment.audio_file == audio_file_path
    
    print(f"Successfully generated audio file: {audio_file_path}")
    
    # Verify file size is reasonable (should be at least a few KB for audio)
    file_size = os.path.getsize(audio_file_path)
    assert file_size > 1000, f"Audio file size is too small: {file_size} bytes"
    
    print(f"Audio file size: {file_size} bytes") 