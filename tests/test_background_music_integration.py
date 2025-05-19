import pytest
import os
import sys
import uuid
from datetime import datetime
import tempfile
import shutil
import subprocess
import base64

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logging import SessionLogger
SessionLogger.start_session(f"test_background_music_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

from db import models, crud
from utils.config import settings
from services.background_music import (
    generate_background_music_prompt,
    generate_background_music,
    process_background_music_for_text
)

# Verify required API keys are present
if not settings.ANTHROPIC_API_KEY or len(settings.ANTHROPIC_API_KEY) < 10:
    raise ValueError("Valid ANTHROPIC_API_KEY required for background music test")

if not os.environ.get("REPLICATE_API_TOKEN") or len(os.environ.get("REPLICATE_API_TOKEN")) < 10:
    pytest.skip("Valid REPLICATE_API_TOKEN required for background music test", allow_module_level=True)

@pytest.fixture(scope="module")
def temp_audio_dir():
    """Create a temporary directory for test audio files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up after tests
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_text(db_session):
    """Create a test text entry in the database using the fixture content or reuse existing"""
    # Check if test text with the same title already exists
    title = "Background Music Test Text"
    existing_test = db_session.query(models.Text).filter(models.Text.title == title).first()
    
    if existing_test:
        # Reuse the existing test record
        yield existing_test
        return
        
    # Create a new test record if none exists
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "text_bg_music_test")
    with open(fixture_path, "r") as file:
        text_content = file.read()
    
    db_text = crud.create_text(db_session, content=text_content, title=title)
    yield db_text
    
    # No cleanup - records remain in DB for inspection

@pytest.fixture
def test_narration_audio(temp_audio_dir):
    """
    Create a test narration audio file with a fixed duration of 30 seconds
    using ffmpeg to generate silence
    """
    # Generate 30 seconds of silence as test audio
    audio_path = os.path.join(temp_audio_dir, "test_narration.mp3")
    
    # Use ffmpeg to generate silence
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',              # Use lavfi input format
        '-i', 'anullsrc=r=44100:cl=stereo',  # Generate silent audio
        '-t', '30',                 # Duration: 30 seconds
        '-c:a', 'libmp3lame',       # Use MP3 codec
        '-q:a', '2',                # Quality setting
        '-y',                       # Overwrite if exists
        audio_path                  # Output file
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    
    # Verify file was created and has expected properties
    assert os.path.exists(audio_path), f"Failed to create test audio file at {audio_path}"
    
    yield audio_path

@pytest.fixture
def test_segment(db_session, test_text, test_narration_audio):
    """Create a test segment with the narration audio file"""
    # Check if a segment already exists for this text
    existing_segment = db_session.query(models.TextSegment).filter(
        models.TextSegment.text_id == test_text.id,
        models.TextSegment.sequence == 1
    ).first()
    
    if existing_segment:
        # Update the existing segment with the current audio path
        existing_segment.audio_file = test_narration_audio
        db_session.commit()
        db_session.refresh(existing_segment)
        yield existing_segment
        return
    
    # Create a segment with the audio file
    segment = crud.create_text_segment(
        db_session,
        text_id=test_text.id,
        character_id=None,  # Character not needed for background music tests
        text="Test text for background music generation.",
        sequence=1,
        audio_file=test_narration_audio
    )
    
    yield segment

@pytest.mark.integration
def test_generate_background_music_prompt(db_session, test_text):
    """Test generating background music prompt using Claude API"""
    # Generate music prompt
    music_prompt = generate_background_music_prompt(db=db_session, text_id=test_text.id)
    
    # Verify prompt was generated
    assert music_prompt is not None, "Music prompt should not be None"
    assert len(music_prompt) > 10, "Music prompt should have reasonable length"
    
    # Verify prompt was saved to database
    db_session.refresh(test_text)
    assert test_text.background_music_prompt == music_prompt, "Prompt should be saved to database"
    
    print(f"Generated music prompt: {music_prompt}")

@pytest.mark.integration
def test_generate_background_music(db_session, test_text, test_segment):
    """Test generating background music using Replicate API and storing in DB"""
    # First ensure we have a prompt
    if not test_text.background_music_prompt:
        music_prompt = generate_background_music_prompt(db=db_session, text_id=test_text.id)
        assert music_prompt is not None, "Failed to generate music prompt"
    
    # Generate background music
    success = generate_background_music(db=db_session, text_id=test_text.id)
    
    # Verify music was generated and stored
    assert success is True, "Background music generation should succeed"
    
    # Verify the base64 data was stored
    db_session.refresh(test_text)
    assert test_text.background_music_audio_b64 is not None, "Background music should be stored in DB"
    assert len(test_text.background_music_audio_b64) > 1000, "Background music data should have reasonable size"
    
    # Try to decode the base64 to ensure it's valid
    try:
        audio_bytes = base64.b64decode(test_text.background_music_audio_b64)
        assert len(audio_bytes) > 1000, "Decoded audio data should have reasonable size"
    except Exception as e:
        pytest.fail(f"Failed to decode base64 audio data: {str(e)}")
    
    print(f"Generated background music: {len(test_text.background_music_audio_b64)} bytes of base64 data")

@pytest.mark.integration
def test_end_to_end_process(db_session, test_text, test_segment):
    """Test the end-to-end background music processing pipeline"""
    # Process background music for the text
    prompt_success, prompt, music_success = process_background_music_for_text(db=db_session, text_id=test_text.id)
    
    # Verify process was successful
    assert prompt_success is True, "Background music prompt generation should succeed"
    assert prompt is not None, "Music prompt should not be None"
    assert music_success is True, "Music generation should succeed"
    
    # Verify data was stored in the database
    db_session.refresh(test_text)
    assert test_text.background_music_audio_b64 is not None, "Background music should be stored in DB"
    assert len(test_text.background_music_audio_b64) > 1000, "Background music data should have reasonable size"
    
    print(f"Successfully processed background music:")
    print(f"Prompt: {prompt}")
    print(f"Music in DB: {len(test_text.background_music_audio_b64)} bytes of base64 data")

# Add this at the end of the file
if __name__ == "__main__":
    # Run the tests directly when this file is executed
    pytest.main(["-xvs", __file__]) 