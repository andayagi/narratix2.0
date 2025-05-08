import pytest
import os
import time
import sys

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
    
    # Characters will be deleted automatically due to cascade relationship with text
    
    return voice_deletion_results

def test_full_text_to_audio_processing():
    """End-to-end test that processes text from a fixture file to audio output through the API"""
    # Step 1: Read the text fixture
    fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'text_full_test')
    text_content = read_fixture(fixture_path)
    assert text_content, "Fixture text should not be empty"
    
    # Step 2: Check if text already exists in the database
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
    
    # If text already exists and is analyzed, ask user if they want to re-analyze
    if text_data["analyzed"]:
        print(f"\nText with ID {text_id} is already analyzed.")
        user_input = input("Would you like to re-analyze it? (y/n): ").lower().strip()
        
        if user_input == 'y':
            # Get all characters for the text
            response = client.get(f"/api/character/text/{text_id}")
            assert response.status_code == 200, "Failed to retrieve characters"
            characters = response.json()
            
            # Delete existing resources
            deletion_results = delete_related_resources(text_id, characters)
            for result in deletion_results:
                print(result)
            
            # Re-analyze the text
            response = client.put(f"/api/text/{text_id}/analyze", params={"force": True})
            assert response.status_code == 200, f"Failed to re-analyze text: {response.text}"
            print(f"Text {text_id} has been re-analyzed")
        else:
            print("Continuing with existing text analysis")
    else:
        # Step 3: Analyze the text via API (if not already analyzed)
        response = client.put(f"/api/text/{text_id}/analyze")
        assert response.status_code == 200, f"Failed to analyze text: {response.text}"
    
    # Step 4: Verify analysis results
    response = client.get(f"/api/text/{text_id}")
    assert response.status_code == 200
    text_data = response.json()
    assert text_data["analyzed"], "Text should be marked as analyzed"
    
    # Step 4.5: Generate voices for characters
    # Get all characters for the text
    response = client.get(f"/api/character/text/{text_id}")
    assert response.status_code == 200, "Failed to retrieve characters"
    characters = response.json()
    
    # Generate a voice for each character
    for character in characters:
        response = client.post(
            f"/api/character/{character['id']}/voice",
            json={
                "text_id": text_id
            }
        )
        assert response.status_code == 200, f"Failed to generate voice for character {character['id']}"
    
    # Step 5: Generate audio for the text via API
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
    print(f"Successfully generated audio file with size: {file_size} bytes")

SessionLogger.start_session("test_end_to_end") 