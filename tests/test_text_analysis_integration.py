import sys
import os
import datetime
import httpx

# Add the project root to the Python path to allow direct script execution
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from sqlalchemy.orm import Session
import uuid
from sqlalchemy import text

# Assuming your project structure allows these imports
from db import models, crud
from services.text_analysis import process_text_analysis
from db.database import SessionLocal, engine, Base, DATABASE_URL # Or however you get your test session
from utils.config import setup_run_logging, Settings
from hume import HumeClient

# Define a long timeout for HTTP requests
LONG_TIMEOUT = 600.0

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Placeholder for test database setup/teardown if needed
# You might use pytest fixtures for this (e.g., setting up a test DB)

# Load test content from fixture file using absolute path
fixture_file = '/Users/anatburg/Narratix2.0/tests/fixtures/text_analysis_example'
with open(fixture_file, 'r', encoding='utf-8') as f:
    BASE_TEST_TEXT_CONTENT = f.read()

def count_words(text):
    """Count words in a text string"""
    return len(text.split())

def delete_related_resources(text_id, db):
    """Delete resources related to text: characters, segments, and Hume voices"""
    # Get characters for voice deletion
    if isinstance(text_id, str) and text_id.isdigit():
        # Convert string numeric ID to int
        text_id = int(text_id)
    
    # Get the text to retrieve its ID
    text = db.query(models.Text).filter(models.Text.id == text_id).first()
    if not text:
        print(f"No text found with ID {text_id}")
        return False
    
    # Use the integer ID directly since the schema uses Integer not UUID
    text_id = text.id
    
    characters = db.query(models.Character).filter(models.Character.text_id == text_id).all()
    
    # Step 1: Delete Hume voices first
    settings = Settings()
    api_key = os.getenv("HUME_API_KEY") or settings.HUME_API_KEY
    
    # Create a custom client with long timeout for Hume API
    hume_http_client = httpx.Client(timeout=LONG_TIMEOUT)
    hume_client = HumeClient(api_key=api_key, httpx_client=hume_http_client)
    
    # Delete Hume voices that end with "_[text_id]"
    voice_deletion_failures = []
    try:
        # List all custom voices
        voices_pager = hume_client.tts.voices.list(provider="CUSTOM_VOICE")
        # Convert pager to list
        voices = list(voices_pager)
        print(f"Found {len(voices)} custom voices in Hume")
        
        # Find and delete voices that end with "_[text_id]" (case insensitive)
        target_suffix = f"_{text_id}"
        deleted_voices = []
        
        for voice in voices:
            if hasattr(voice, "name") and (
                voice.name.endswith(target_suffix) or 
                voice.name.lower().endswith(target_suffix.lower())
            ):
                try:
                    print(f"Deleting voice '{voice.name}'")
                    hume_client.tts.voices.delete(name=voice.name)
                    deleted_voices.append(voice.name)
                except Exception as e:
                    error_msg = f"Failed to delete voice '{voice.name}': {str(e)}"
                    voice_deletion_failures.append(error_msg)
                    print(error_msg)
        
        if deleted_voices:
            print(f"Successfully deleted {len(deleted_voices)} voice(s) for text_id {text_id}")
        else:
            print(f"No voices found ending with '_{text_id}'")
            
    except Exception as e:
        error_msg = f"Failed to list or delete voices: {str(e)}"
        voice_deletion_failures.append(error_msg)
        print(error_msg)
    
    # If any voice deletion failed, return false WITHOUT deleting from database
    if voice_deletion_failures:
        error_summary = "\n".join(voice_deletion_failures)
        print(f"Warning: Voice deletions failed:\n{error_summary}")
        print("Database records will not be deleted to maintain consistency.")
        return False
    
    # Step 2: Only delete database records if ALL Hume voices were successfully deleted
    
    # Delete segments
    deleted_segments = crud.delete_segments_by_text(db, text_id)
    print(f"Deleted {deleted_segments} segments for text {text_id}")
    
    # Delete characters from database
    deleted_characters = crud.delete_characters_by_text(db, text_id)
    print(f"Deleted {deleted_characters} characters for text {text_id}")
    
    return True  # All deletions were successful

@pytest.mark.integration  # Mark as integration test
def test_full_text_analysis_pipeline():
    """
    Tests the full text analysis pipeline from text input to DB records,
    using the real Anthropic API. Requires ANTHROPIC_API_KEY environment variable.
    """
    # Setup a single logging session for all operations in this test
    session_id = setup_run_logging("test_text_analysis_integration")
    
    print(f"DATABASE_URL used in test: {DATABASE_URL}")
    print(f"Engine URL used in test: {engine.url}")
    
    # Create a regular database session
    db = SessionLocal()
    try:
        # Check if text with this content already exists
        existing_text = crud.get_text_by_content(db, BASE_TEST_TEXT_CONTENT)
        
        if existing_text:
            print(f"Found existing text with ID: {existing_text.id}")
            text_id = existing_text.id
            
            print(f"Will delete existing resources and replace analysis")
            
            # Delete related resources before reanalysis
            deletion_successful = delete_related_resources(text_id, db)
            if not deletion_successful:
                print("Test aborted: Failed to delete related resources")
                return  # Exit the test if deletion fails
            
            # Store the original timestamp directly from the database to avoid timezone issues
            result = db.execute(text("SELECT last_updated FROM texts WHERE id = :id"), {"id": text_id})
            original_timestamp_str = result.scalar()
            print(f"Original last_updated from DB: {original_timestamp_str}")
            
            # Set analyzed to False to ensure reanalysis if process_text_analysis relies on it
            # or if we want to simulate a full re-processing flow.
            existing_text.analyzed = False  # Ensure it gets re-analyzed by process_text_analysis
            db.commit()
            db.refresh(existing_text)
            
            db_text = existing_text
        else:
            # 1. Setup: Create initial Text record
            db_text = crud.create_text(db, content=BASE_TEST_TEXT_CONTENT, title="Integration Test Text")
            assert db_text is not None
            text_id = db_text.id  # Use the ID directly
            assert db_text.analyzed is False
            original_timestamp_str = None  # No original timestamp for new records
            
            print(f"Created new text with ID: {text_id}")
            
            # Force commit to ensure the record is saved
            db.commit()
        
        # 2. Execute: Run the processing function
        # This will call the real Anthropic API
        try:
            updated_db_text = process_text_analysis(db=db, text_id=text_id, content=BASE_TEST_TEXT_CONTENT)
        except ValueError as e:
            # Check if this is a truncation error
            if "truncated" in str(e).lower() or "expecting ',' delimiter" in str(e).lower():
                print(f"\n=== API RESPONSE TRUNCATION ERROR ===")
                print(f"Text ID: {text_id}")
                print(f"Content length: {len(BASE_TEST_TEXT_CONTENT)} characters")
                print(f"Error: {e}")
                print("The Anthropic API response was cut off/truncated, likely due to response size limits.")
                print("Consider breaking the text into smaller chunks or increasing max_tokens.")
                print("=====================================\n")
                # Re-raise the error to fail the test
                raise e
            else:
                # Re-raise other errors
                raise e

        # 3. Verify: Check results in the database
        db.refresh(updated_db_text)

        # Verify Text record update
        assert updated_db_text.analyzed is True
        
        # If this was an update, verify the last_updated timestamp was changed
        if original_timestamp_str:
            # Get the new timestamp directly from the database to avoid timezone issues
            result = db.execute(text("SELECT last_updated FROM texts WHERE id = :id"), {"id": text_id})
            new_timestamp_str = result.scalar()
            print(f"New last_updated from DB: {new_timestamp_str}")
            
            # Compare the raw timestamp strings
            assert new_timestamp_str != original_timestamp_str, "last_updated timestamp wasn't updated"

        # Verify Characters
        characters = db.query(models.Character).filter(models.Character.text_id == text_id).all()
        assert len(characters) > 0 # Basic check, refine later
        print(f"Found characters: {[c.name for c in characters]}")

        # Verify Segments
        segments = db.query(models.TextSegment).filter(models.TextSegment.text_id == text_id).order_by(models.TextSegment.sequence).all()
        assert len(segments) > 0 # Basic check, refine later
        print(f"Found {len(segments)} segments.")

        # Count and compare words
        input_word_count = count_words(BASE_TEST_TEXT_CONTENT)
        
        # Combine all segment content and count words
        all_segments_content = " ".join([segment.text for segment in segments if segment.text])
        segments_word_count = count_words(all_segments_content)
        
        # Force output to always show
        word_comparison_output = f"""
=== WORD COUNT COMPARISON ===
Input text words: {input_word_count}
Segments words: {segments_word_count}
Difference: {segments_word_count - input_word_count}
Coverage: {(segments_word_count / input_word_count * 100):.1f}%
=============================
"""
        
        # Force output to terminal using multiple approaches
        sys.stdout.write(word_comparison_output + "\n")
        sys.stdout.flush()
        print(word_comparison_output, flush=True)
        
        # Also log to pytest's output - always show as warning, don't fail test
        import warnings
        warnings.warn(f"Word count analysis:{word_comparison_output}")

        # Explicitly commit any remaining changes to keep data in database
        db.commit()
        
        print(f"Test completed. Data for text ID {text_id} is preserved in database.")

    finally:
        # Always close the session, but don't rollback
        db.close() 