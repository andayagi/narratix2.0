import pytest
import os
import uuid
from datetime import datetime
import base64

from utils.logging import SessionLogger
SessionLogger.start_session(f"test_speech_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

from db import models, crud
from utils.config import settings
from services.speech_generation import generate_text_audio

# Skip the test if HUME_API_KEY is not available or invalid
if not settings.HUME_API_KEY or len(settings.HUME_API_KEY) < 10:
    pytest.skip("Valid HUME_API_KEY required for integration test", allow_module_level=True)

# db_session fixture is imported from conftest.py

# Voice IDs
MAN_VOICE_ID = "a9f41985-fc78-4081-b1ab-9e20aa360385"
WOMAN_VOICE_ID = "bd59eb6c-4d73-402c-8537-a69a8e147ab5"  

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
        assert segment.audio_data_b64 is None
    
    # Generate audio using REAL API call
    success = generate_text_audio(db=db_session, text_id=test_text.id)
    
    # Verify audio was generated successfully
    assert success is True, "Audio generation should return True on success"
    
    # Force a complete refresh from database with separate queries
    refreshed_segments = []
    for segment in segments:
        # Get a fresh instance from the database
        fresh_segment = db_session.query(models.TextSegment).filter(
            models.TextSegment.id == segment.id
        ).first()
        refreshed_segments.append(fresh_segment)
    
    # Verify each segment has audio data
    for segment in refreshed_segments:
        # Check if audio_data_b64 exists and is not None or empty
        print(f"Segment {segment.id} retrieved audio_data_b64: '{segment.audio_data_b64}'")
        assert segment.audio_data_b64 is not None, f"Segment {segment.id} has NULL audio_data_b64"
        assert segment.audio_data_b64 != "", f"Segment {segment.id} has empty audio_data_b64"
        
        # Verify audio data is a valid base64 string with reasonable size
        try:
            audio_bytes = base64.b64decode(segment.audio_data_b64)
            assert len(audio_bytes) > 1000, f"Audio data for segment {segment.id} is too small: {len(audio_bytes)} bytes"
            print(f"Segment {segment.id} audio data size: {len(audio_bytes)} bytes")
        except Exception as e:
            assert False, f"Failed to decode base64 for segment {segment.id}: {str(e)}"
    
    print(f"Successfully generated audio data for {len(segments)} segments") 