import pytest
import os
import time
import sys

"""
End-to-end test for the text-to-audio processing pipeline.

To run this test:
    pytest tests/test_end_to_end.py -v

When running the test with pre-existing text:
    - By default, it will create a new text record
    - To re-analyze existing text instead, set REANALYZE=1:
        REANALYZE=1 pytest tests/test_end_to_end.py -v
"""

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
import os.path
from api.main import app
from db.database import get_db, SessionLocal
from utils.logging import SessionLogger
import utils.http_client

# Initialize Hume client for voice deletion
from hume import HumeClient
from utils.config import Settings

# Create test client
client = TestClient(app)

def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def read_fixture(file_path):
    """Read content from a test fixture file"""
    with open(file_path, 'r') as f:
        return f.read()

def delete_related_resources(text_id, characters):
    """Delete resources related to text: characters, segments, and Hume voices"""
    db = next(override_get_db())
    
    # Delete segments
    from db import crud
    deleted_segments = crud.delete_segments_by_text(db, text_id)
    print(f"Deleted {deleted_segments} segments for text {text_id}")
    
    # Delete Hume voices
    settings = Settings()
    api_key = os.getenv("HUME_API_KEY") or settings.HUME_API_KEY
    hume_client = HumeClient(api_key=api_key)
    
    voice_deletion_results = []
    for character in characters:
        if character['provider_id']:
            try:
                hume_client.tts.voices.delete(id=character['provider_id'])
                voice_deletion_results.append(f"Deleted voice {character['provider_id']} for {character['name']}")
            except Exception as e:
                voice_deletion_results.append(f"Failed to delete voice for {character['name']}: {str(e)}")
    
    # Delete characters from database
    deleted_characters = crud.delete_characters_by_text(db, text_id)
    print(f"Deleted {deleted_characters} characters for text {text_id}")
    
    return voice_deletion_results

def prompt_for_reanalysis():
    """
    Determine whether to reanalyze based on environment variable
    or default to False (create new)

    Set environment variable REANALYZE=1 to re-analyze existing text
    """
    import os
    
    # Check for environment variable
    reanalyze = os.getenv("REANALYZE", "0").strip()
    
    if reanalyze == "1":
        print("Choosing option 1: Re-analyze (based on REANALYZE environment variable)")
        return True
    else:
        print("Choosing option 2: Create new records (default or REANALYZE=0)")
        return False

def test_full_text_to_audio_processing():
    """End-to-end test that processes text from a fixture file to audio output through the API"""
    # Step 1: Read the text fixture
    fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'text_full_test')
    text_content = read_fixture(fixture_path)
    assert text_content, "Fixture text should not be empty"
    
    # Step 2: Check if text already exists in the database
    print("\n----- Creating or finding text in database -----")
    response = client.post(
        "/api/text/",
        json={
            "content": text_content,
            "title": "E2E Test Text"
        }
    )
    assert response.status_code == 200, f"Failed to create or find text: {response.text}"
    text_data = response.json()
    text_id = text_data["id"]
    
    # Explicitly check whether the text was created or found
    # First check if 'created' property exists in the response (for backward compatibility)
    pre_existing = False
    if "created" in text_data:
        # Use the 'created' flag directly from the API
        pre_existing = not text_data["created"]
        if pre_existing:
            print(f"FOUND: Text with ID {text_id} already exists in the database.")
        else:
            print(f"CREATED: New text with ID {text_id} has been created in the database.")

    # If text already exists and is analyzed, prompt user for action
    if pre_existing:
        reanalyze = prompt_for_reanalysis()
        
        if reanalyze:
            print(f"\n----- Reanalyzing existing text -----")
            
            # Get all characters for the text
            response = client.get(f"/api/character/text/{text_id}")
            assert response.status_code == 200, "Failed to retrieve characters"
            characters = response.json()
            
            # Delete existing resources
            deletion_results = delete_related_resources(text_id, characters)
            for result in deletion_results:
                print(result)
            
            # Re-analyze the text
            response = client.post(f"/api/text-analysis/{text_id}/analyze")
            assert response.status_code in [200, 202], f"Expected 200 or 202, got {response.status_code}: {response.text}"

            # Wait a moment for background processing if it returns 202
            if response.status_code == 202:
                time.sleep(2)
            
            # Verify analysis was performed
            response = client.get(f"/api/text/{text_id}")
            text_data = response.json()
            
            # The analyzed field might not be immediately updated for background tasks
            # But we can check if characters and segments were created
            response = client.get(f"/api/character/")
            characters = response.json()
            assert len(characters) > 0, "Should have characters after analysis"
            
            # Test duplicate analysis (should not re-analyze unless force=True)
            response = client.post(f"/api/text-analysis/{text_id}/analyze")
            assert response.status_code in [200, 202], f"Expected 200 or 202, got {response.status_code}"
            
            # Test duplicate analysis again
            response = client.post(f"/api/text-analysis/{text_id}/analyze")
            assert response.status_code in [200, 202], f"Expected 200 or 202, got {response.status_code}"
        else:
            # Create new text record instead
            print(f"\n----- Creating new text record -----")
            response = client.post(
                "/api/text/",
                json={
                    "content": text_content,
                    "title": "E2E Test Text (New)",
                    "force_new": True
                }
            )
            assert response.status_code == 200, f"Failed to create new text: {response.text}"
            text_data = response.json()
            text_id = text_data["id"]
            print(f"Created new text with ID {text_id}")
            
            # Analyze the new text
            response = client.post(f"/api/text-analysis/{text_id}/analyze")
            assert response.status_code in [200, 202], f"Expected 200 or 202, got {response.status_code}: {response.text}"

            # Wait a moment for background processing if it returns 202
            if response.status_code == 202:
                time.sleep(2)
            
            # Verify analysis was performed
            response = client.get(f"/api/text/{text_id}")
            text_data = response.json()
            
            # The analyzed field might not be immediately updated for background tasks
            # But we can check if characters and segments were created
            response = client.get(f"/api/character/")
            characters = response.json()
            assert len(characters) > 0, "Should have characters after analysis"
            
            # Test duplicate analysis (should not re-analyze unless force=True)
            response = client.post(f"/api/text-analysis/{text_id}/analyze")
            assert response.status_code in [200, 202], f"Expected 200 or 202, got {response.status_code}"
            
            # Test duplicate analysis again
            response = client.post(f"/api/text-analysis/{text_id}/analyze")
            assert response.status_code in [200, 202], f"Expected 200 or 202, got {response.status_code}"
    else:
        # Step 3: Analyze the text via API (if not already analyzed)
        print(f"\n----- Analyzing new text -----")
        response = client.post(f"/api/text-analysis/{text_id}/analyze")
        assert response.status_code in [200, 202], f"Expected 200 or 202, got {response.status_code}: {response.text}"

        # Wait a moment for background processing if it returns 202
        if response.status_code == 202:
            time.sleep(2)
        
        # Verify analysis was performed
        response = client.get(f"/api/text/{text_id}")
        text_data = response.json()
        
        # The analyzed field might not be immediately updated for background tasks
        # But we can check if characters and segments were created
        response = client.get(f"/api/character/")
        characters = response.json()
        assert len(characters) > 0, "Should have characters after analysis"
        
        # Test duplicate analysis (should not re-analyze unless force=True)
        response = client.post(f"/api/text-analysis/{text_id}/analyze")
        assert response.status_code in [200, 202], f"Expected 200 or 202, got {response.status_code}"
        
        # Test duplicate analysis again
        response = client.post(f"/api/text-analysis/{text_id}/analyze")
        assert response.status_code in [200, 202], f"Expected 200 or 202, got {response.status_code}"
    
    # Step 4: Verify analysis results
    response = client.get(f"/api/text/{text_id}")
    assert response.status_code == 200
    text_data = response.json()
    assert text_data["analyzed"], "Text should be marked as analyzed"
    
    # Step 4.5: Generate voices for characters
    print(f"\n----- Generating voices for characters -----")
    # Get all characters for the text
    response = client.get(f"/api/character/text/{text_id}")
    assert response.status_code == 200, "Failed to retrieve characters"
    characters = response.json()
    
    # Generate a voice for each character
    for character in characters:
        print(f"Generating voice for character: {character['name']}")
        response = client.post(
            f"/api/character/{character['id']}/voice",
            json={
                "text_id": text_id
            }
        )
        assert response.status_code == 200, f"Failed to generate voice for character {character['id']}"
    
    # Step 5: Generate audio for the text via API
    print(f"\n----- Generating audio for text -----")
    response = client.post(f"/api/audio/text/{text_id}/generate")
    assert response.status_code == 200, f"Failed to generate audio: {response.text}"
    audio_data = response.json()
    
    # Step 6: Verify audio was generated
    assert "audio_file" in audio_data, "Response should include audio file path"
    assert audio_data["audio_file"], "Audio file path should not be empty"
    
    # Step 7: Get generated audio file
    audio_file_name = os.path.basename(audio_data["audio_file"])
    response = client.get(f"/api/audio/file/{audio_file_name}")
    assert response.status_code == 200, "Failed to retrieve audio file"
    
    # Step 8: Save and verify the audio file
    output_path = "output/e2e_test_output.mp3"
    with open(output_path, "wb") as f:
        f.write(response.content)
    
    # Step 9: Verify audio file is valid by checking file size instead of using AudioSegment
    file_size = os.path.getsize(output_path)
    assert file_size > 0, "Audio file should not be empty"
    print(f"\nSuccess! Generated audio file with size: {file_size} bytes at {output_path}")

SessionLogger.start_session("test_end_to_end") 