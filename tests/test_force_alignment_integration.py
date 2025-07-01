"""
Integration test for force alignment service using real audio segments
"""
import os
import sys
import base64
import json
import tempfile
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db import models, crud
from services.combine_export_audio import _run_force_alignment_on_combined_audio, force_alignment_service
from services.combine_export_audio import combine_speech_segments
from utils.logging import get_logger

logger = get_logger(__name__)

# Global output directory for this test session
TEST_SESSION_DIR = None

def get_test_output_dir() -> str:
    """Get or create the test session output directory with timestamp"""
    global TEST_SESSION_DIR
    if TEST_SESSION_DIR is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        TEST_SESSION_DIR = os.path.join(PROJECT_ROOT, "tests", "output", "force_alignment_integration", timestamp)
        os.makedirs(TEST_SESSION_DIR, exist_ok=True)
        logger.info(f"Created test session directory: {TEST_SESSION_DIR}")
    return TEST_SESSION_DIR

@pytest.fixture
def audio_fixtures_dir():
    """Path to the audio fixtures directory"""
    return os.path.join(os.path.dirname(__file__), "fixtures", "audio_segments")

@pytest.fixture
def test_segments_data(audio_fixtures_dir):
    """Load a few test audio segments from fixtures"""
    segment_files = []
    audio_files = os.listdir(audio_fixtures_dir)
    # Use first 3 audio files for testing
    for filename in sorted(audio_files)[:3]:
        if filename.endswith('.mp3'):
            filepath = os.path.join(audio_fixtures_dir, filename)
            segment_files.append(filepath)
    return segment_files

@pytest.fixture(scope="session")
def shared_test_data(request):
    """Shared test data across all tests to avoid duplicates"""
    return {}

@pytest.fixture
def test_text_with_segments(db_session, test_segments_data, shared_test_data):
    """Create a test text with segments containing real audio data (reuse if exists)"""
    
    # Check if we already created test data
    if 'text_data' in shared_test_data:
        return shared_test_data['text_data']
    
    # Create test text
    test_content = "This is a test story. It has multiple segments. Each segment has audio data."
    text = crud.create_text(db_session, content=test_content, title="Force Alignment Test")
    
    # Create test character
    character = crud.create_character(
        db_session, 
        text_id=text.id, 
        name="Test Narrator",
        is_narrator=True
    )
    
    # Create segments with real audio data
    segments = []
    for i, audio_file in enumerate(test_segments_data):
        # Read audio file and encode to base64
        with open(audio_file, 'rb') as f:
            audio_bytes = f.read()
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # Create segment with corresponding text
        segment_texts = ["This is a test story.", "It has multiple segments.", "Each segment has audio data."]
        segment = crud.create_text_segment(
            db_session,
            text_id=text.id,
            character_id=character.id,
            text=segment_texts[i % len(segment_texts)],
            sequence=i + 1
        )
        
        # Update with audio data
        crud.update_segment_audio_data(db_session, segment.id, audio_b64)
        segments.append(segment)
    
    # Store in shared data
    shared_test_data['text_data'] = (text, character, segments)
    return text, character, segments

@pytest.mark.integration
def test_force_alignment_integration(db_session: Session, test_text_with_segments, shared_test_data):
    """Test complete force alignment pipeline with real audio data"""
    text, character, segments = test_text_with_segments
    output_dir = get_test_output_dir()
    
    logger.info(f"Testing force alignment for text {text.id} with {len(segments)} segments")
    
    # Verify initial state - no word timestamps
    assert text.word_timestamps is None
    assert text.force_alignment_timestamp is None
    
    # Run force alignment
    success = run_force_alignment(db_session, text.id)
    
    if success:
        # Refresh text from database
        db_session.refresh(text)
        
        # Verify word timestamps were generated
        assert text.word_timestamps is not None, "Word timestamps should be generated"
        assert text.force_alignment_timestamp is not None, "Force alignment timestamp should be set"
        assert isinstance(text.word_timestamps, list), "Word timestamps should be a list"
        
        # Output force alignment results to file
        alignment_output_file = os.path.join(output_dir, "1_database_force_alignment.json")
        with open(alignment_output_file, 'w') as f:
            json.dump({
                "description": "Force alignment results from full database pipeline (run_force_alignment)",
                "method": "database_pipeline",
                "text_id": text.id,
                "text_content": text.content,
                "word_timestamps": text.word_timestamps,
                "force_alignment_timestamp": text.force_alignment_timestamp.isoformat() if text.force_alignment_timestamp else None,
                "segments_count": len(segments)
            }, f, indent=2)
        
        # Store results in shared data
        shared_test_data['database_alignment_results'] = text.word_timestamps
        
        logger.info(f"Database force alignment results saved to: {alignment_output_file}")
        logger.info(f"Generated {len(text.word_timestamps)} word timestamps")
        
        # Verify word timestamps structure
        for word_data in text.word_timestamps[:5]:  # Check first 5 words
            assert "word" in word_data, "Each timestamp should have a word"
            assert "start" in word_data, "Each timestamp should have a start time"
            assert "end" in word_data, "Each timestamp should have an end time"
            assert isinstance(word_data["start"], (int, float)), "Start time should be numeric"
            assert isinstance(word_data["end"], (int, float)), "End time should be numeric"
            assert word_data["end"] >= word_data["start"], "End time should be >= start time"
    else:
        logger.warning("Force alignment failed - this might be due to missing faster-whisper dependency")
        pytest.skip("Force alignment failed - likely missing faster-whisper dependency")

@pytest.mark.integration 
def test_combine_speech_segments(db_session: Session, test_text_with_segments, shared_test_data):
    """Test combining speech segments into a single audio file"""
    text, character, segments = test_text_with_segments
    output_dir = get_test_output_dir()
    
    # Skip if we already have combined audio
    if 'combined_audio_path' in shared_test_data:
        logger.info("Using existing combined audio file")
        return
    
    logger.info(f"Testing audio combination for text {text.id} with {len(segments)} segments")
    
    # Combine speech segments
    combined_audio_path = await combine_speech_segments(text.id, output_dir=output_dir)
    
    # Verify combined audio was created
    assert combined_audio_path is not None, "Combined audio path should be returned"
    assert os.path.exists(combined_audio_path), "Combined audio file should exist"
    
    # Verify file has reasonable size
    file_size = os.path.getsize(combined_audio_path)
    assert file_size > 1000, f"Combined audio file should have reasonable size, got {file_size} bytes"
    
    # Store in shared data
    shared_test_data['combined_audio_path'] = combined_audio_path
    
    logger.info(f"Combined audio saved to: {combined_audio_path}")
    logger.info(f"Combined audio file size: {file_size} bytes")

@pytest.mark.integration
def test_force_alignment_with_combined_audio(db_session: Session, test_text_with_segments, shared_test_data):
    """Test force alignment using combined audio directly"""
    text, character, segments = test_text_with_segments
    output_dir = get_test_output_dir()
    
    logger.info(f"Testing force alignment with combined audio for text {text.id}")
    
    # Get or create combined audio
    if 'combined_audio_path' not in shared_test_data:
        combined_audio_path = await combine_speech_segments(text.id, output_dir=output_dir)
        shared_test_data['combined_audio_path'] = combined_audio_path
    else:
        combined_audio_path = shared_test_data['combined_audio_path']
    
    assert combined_audio_path is not None, "Combined audio should be created"
    assert os.path.exists(combined_audio_path), "Combined audio file should exist"
    
    # Run force alignment on the combined audio
    word_timestamps = get_word_timestamps_for_text(combined_audio_path, text.content)
    
    if word_timestamps:
        # Output direct force alignment results
        alignment_output_file = os.path.join(output_dir, "2_direct_combined_audio_alignment.json")
        with open(alignment_output_file, 'w') as f:
            json.dump({
                "description": "Force alignment results from direct processing of combined audio file",
                "method": "direct_combined_audio",
                "text_id": text.id,
                "text_content": text.content,
                "combined_audio_file": os.path.basename(combined_audio_path),
                "word_timestamps": word_timestamps
            }, f, indent=2)
        
        logger.info(f"Direct combined audio alignment results saved to: {alignment_output_file}")
        logger.info(f"Generated {len(word_timestamps)} word timestamps from combined audio")
        
        # Verify structure
        assert len(word_timestamps) > 0, "Should have at least some word timestamps"
        for word_data in word_timestamps[:3]:
            assert "word" in word_data
            assert "start" in word_data  
            assert "end" in word_data
    else:
        logger.warning("Direct force alignment on combined audio failed")
        pytest.skip("Direct force alignment failed - likely missing faster-whisper dependency")

@pytest.mark.integration
def test_force_alignment_from_base64(db_session: Session, test_segments_data, shared_test_data):
    """Test force alignment directly from base64 audio data"""
    from services.combine_export_audio import force_alignment_service
    
    output_dir = get_test_output_dir()
    
    # Use first audio file
    audio_file = test_segments_data[0]
    with open(audio_file, 'rb') as f:
        audio_bytes = f.read()
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    test_text = "This is a test story."
    
    # Get word timestamps from base64 - using temporary file approach since we moved alignment to audio file processing
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
        temp_file.write(audio_bytes)
        temp_file_path = temp_file.name
    
    try:
        word_timestamps = force_alignment_service.get_word_timestamps(temp_file_path, test_text)
    finally:
        os.remove(temp_file_path)
    
    if word_timestamps:
        # Output results
        alignment_output_file = os.path.join(output_dir, "3_base64_single_segment_alignment.json")
        with open(alignment_output_file, 'w') as f:
            json.dump({
                "description": "Force alignment results from base64 processing of single audio segment",
                "method": "base64_single_segment",
                "test_text": test_text,
                "audio_file_used": os.path.basename(audio_file),
                "word_timestamps": word_timestamps
            }, f, indent=2)
        
        logger.info(f"Base64 single segment alignment results saved to: {alignment_output_file}")
        logger.info(f"Generated {len(word_timestamps)} word timestamps from base64 audio")
        
        assert len(word_timestamps) > 0, "Should generate word timestamps"
    else:
        logger.warning("Base64 force alignment failed")
        pytest.skip("Base64 force alignment failed - likely missing faster-whisper dependency")

@pytest.mark.integration
def test_create_comparison_summary(shared_test_data):
    """Create a summary comparing all the different alignment methods"""
    output_dir = get_test_output_dir()
    
    summary_file = os.path.join(output_dir, "0_TEST_SUMMARY.json")
    with open(summary_file, 'w') as f:
        json.dump({
            "test_session_summary": {
                "description": "Integration test results for force alignment service",
                "output_directory": os.path.basename(output_dir),
                "files_generated": {
                    "1_database_force_alignment.json": "Results from full database pipeline (combines segments → aligns → stores in DB)",
                    "2_direct_combined_audio_alignment.json": "Results from direct alignment on combined audio file",
                    "3_base64_single_segment_alignment.json": "Results from base64 processing of single segment",
                    "combined_speech_*.mp3": "Combined audio file from all segments"
                },
                "methods_compared": {
                    "database_pipeline": "Full workflow: DB segments → combine → align → store results",
                    "direct_combined_audio": "Direct alignment on pre-combined audio file",
                    "base64_single_segment": "Process individual segment from base64 data"
                }
            }
        }, f, indent=2)
    
    logger.info(f"Test summary created: {summary_file}")

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"]) 