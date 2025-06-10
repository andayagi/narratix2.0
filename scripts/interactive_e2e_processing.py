#!/usr/bin/env python3
import pytest
import os
import time
import sys
import requests
import datetime
import httpx

"""
Interactive end-to-end script for the text-to-audio processing pipeline.

To run this script:
    python3 scripts/interactive_e2e_processing.py

When running the script with pre-existing text, it will prompt you
to choose whether to re-analyze or create new records.
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
from services.background_music import process_background_music_for_text
from services.combine_export_audio import export_final_audio
import shutil
import tempfile

# Set a very long timeout for HTTP requests (6000 seconds = 100 minutes)
LONG_TIMEOUT = 6000.0
# Override the default HTTP client creation with our long timeout
original_create_client = utils.http_client.create_client
utils.http_client.create_client = lambda **kwargs: original_create_client(timeout=LONG_TIMEOUT, **kwargs)

# Initialize Hume client for voice deletion
from hume import HumeClient
from utils.config import Settings

# Create a direct client instead of TestClient to ensure consistent DB sessions
app.dependency_overrides = {}  # Clear any existing overrides
client = TestClient(app)

def read_file(file_path):
    """Read content from a file"""
    with open(file_path, 'r') as f:
        return f.read()

def delete_related_resources(text_id, characters):
    """Delete resources related to text: characters, segments, and Hume voices"""
    # Create direct session (not generator) to ensure transaction completion
    db = SessionLocal()
    
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
        
        # Log all found voices for debugging
        for voice in voices:
            if hasattr(voice, "name"):
                print(f"Found voice: '{voice.name}'")
        
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
        
    finally:
        # Close HTTP client
        hume_http_client.close()
    
    # If any voice deletion failed, return false WITHOUT deleting from database
    if voice_deletion_failures:
        error_summary = "\n".join(voice_deletion_failures)
        print(f"Warning: Voice deletions failed:\n{error_summary}")
        print("Database records will not be deleted to maintain consistency.")
        db.close()  # Make sure to close the DB connection
        return False
    
    try:
        # Step 2: Only delete database records if ALL Hume voices were successfully deleted
        # Use direct SQL execution for more reliable deletion
        from sqlalchemy import text
        
        # Delete segments first (due to foreign key constraints)
        deleted_segments = db.execute(
            text(f"DELETE FROM text_segments WHERE text_id = :text_id"),
            {"text_id": text_id}
        ).rowcount
        print(f"Deleted {deleted_segments} segments for text {text_id}")
        
        # Then delete characters
        deleted_characters = db.execute(
            text(f"DELETE FROM characters WHERE text_id = :text_id"),
            {"text_id": text_id}
        ).rowcount
        print(f"Deleted {deleted_characters} characters for text {text_id}")
        
        # Commit the transaction
        db.commit()
        return True  # All deletions were successful
        
    except Exception as e:
        db.rollback()  # Rollback transaction on error
        print(f"Error during database deletion: {str(e)}")
        return False
        
    finally:
        db.close()  # Always close the DB connection

def prompt_action_for_existing_analyzed_text():
    """
    Prompt user for action when text already exists and has been analyzed
    """
    print("\nThis text already exists in the database and has been analyzed.")
    print("Options:")
    print("1. Re-analyze (deletes existing characters, segments, and voices)")
    print("2. Re-generate audio (uses existing analysis)")
    print("3. Generate bg music (uses existing speech audio segments)")
    print("4. Combine audio (combine speech segments and bg music)")
    print("5. Abort")
    
    while True:
        choice = input("Enter your choice (1, 2, 3, 4, or 5): ").strip()
        if choice == "1":
            return "reanalyze"
        elif choice == "2":
            return "regenerate"
        elif choice == "3":
            return "generate_bg_music"
        elif choice == "4":
            return "combine_audio"
        elif choice == "5":
            return "abort"
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")

def get_audio_output_path(text_id):
    """Generate and create a date-based directory structure for audio output files"""
    # Create base audio_files directory if it doesn't exist
    audio_dir = os.path.join(PROJECT_ROOT, 'audio_files')
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)
    
    # Create date-based subdirectory
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    date_dir = os.path.join(audio_dir, today)
    if not os.path.exists(date_dir):
        os.makedirs(date_dir)
    
    # Generate timestamped filename
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{text_id}_inter_e2e.mp3"
    return os.path.join(date_dir, filename)

def run_interactive_e2e_flow():
    """End-to-end process for text to audio, with interactive prompts if needed."""
    try:
        # Ask user if they want to use input file or text_id
        print("\n----- Text Source Selection -----")
        print("1. Use input file from scripts/input_interactive_e2e.txt")
        print("2. Use existing text_id")
        
        while True:
            choice = input("Enter your choice (1 or 2): ").strip()
            if choice == "1":
                use_input_file = True
                break
            elif choice == "2":
                use_input_file = False
                text_id = input("Enter the text_id to process: ").strip()
                if not text_id:
                    print("Text ID cannot be empty. Please try again.")
                    continue
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")

        # Process based on user's choice
        if use_input_file:
            # Step 1: Read the text input file
            input_file_path = os.path.join(PROJECT_ROOT, 'scripts', 'input_interactive_e2e.txt')
            text_content = read_file(input_file_path)
            if not text_content:
                raise Exception("Input text file is empty")
            
            # Step 2: Check if text already exists in the database
            print("\n----- Creating or finding text in database -----")
            response = client.post(
                "/api/text/",
                json={
                    "content": text_content,
                    "title": "E2E Test Text"
                }
            )
            if response.status_code != 200:
                raise Exception(f"Failed to create or find text: {response.text}")
            
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
        else:
            # Get text details by ID
            print(f"\n----- Retrieving text with ID {text_id} -----")
            response = client.get(f"/api/text/{text_id}")
            if response.status_code != 200:
                raise Exception(f"Failed to get text: {response.text}")
            
            text_data = response.json()
            pre_existing = True
            print(f"FOUND: Using existing text with ID {text_id} from the database.")

        # Check if pre-existing text is already analyzed
        if pre_existing:
            # Get text details to check if it's analyzed
            response = client.get(f"/api/text/{text_id}")
            if response.status_code != 200:
                raise Exception(f"Failed to get text details: {response.text}")
                
            text_details = response.json()
            is_analyzed = text_details.get("analyzed", False)
            
            # Get all characters for the text to check if it has characters
            response = client.get(f"/api/character/text/{text_id}")
            if response.status_code != 200:
                raise Exception("Failed to retrieve characters")
                
            characters = response.json()
            has_characters = len(characters) > 0
            
            # Initialize action to avoid potential NameError
            action = None
            
            # If text is analyzed and has characters, prompt with three options
            if is_analyzed and has_characters:
                action = prompt_action_for_existing_analyzed_text()
                
                if action == "reanalyze":
                    print(f"\n----- Reanalyzing existing text -----")
                    
                    # Delete existing resources
                    try:
                        deletion_successful = delete_related_resources(text_id, characters)
                        if not deletion_successful:
                            print("\nProcess aborted: Hume voice deletion failed.")
                            return  # Exit the function if deletion fails
                    except Exception as e:
                        print(f"ERROR: {str(e)}")
                        print("\nProcess aborted due to error in resource deletion.")
                        return  # Exit the function if deletion fails
                    
                    # Re-analyze the text
                    response = client.put(f"/api/text/{text_id}/analyze", params={"force": True})
                    if response.status_code != 200:
                        raise Exception(f"Failed to re-analyze text: {response.text}")
                    print(f"Text {text_id} has been re-analyzed")
                elif action == "regenerate":
                    print(f"\n----- Re-generating audio using existing analysis -----")
                    # Skip analysis step, proceed to voice generation
                elif action == "generate_bg_music":
                    print(f"\n----- Generating background music using existing speech audio segments -----")
                    # Skip analysis and voice generation, proceed to bg music generation
                elif action == "combine_audio":
                    print(f"\n----- Combining speech segments and background music -----")
                    # Skip analysis, voice generation, and speech audio generation
                elif action == "abort":
                    print("\nOperation aborted by user.")
                    return  # Exit the function
            else:
                # Text exists but isn't analyzed - automatically analyze it
                print(f"\n----- Analyzing existing text -----")
                response = client.put(f"/api/text/{text_id}/analyze")
                if response.status_code != 200:
                    raise Exception(f"Failed to analyze text: {response.text}")
                print(f"Text {text_id} has been analyzed")
        else:
            # Step 3: Analyze the text via API (if not already analyzed)
            print(f"\n----- Analyzing new text -----")
            response = client.put(f"/api/text/{text_id}/analyze")
            if response.status_code != 200:
                raise Exception(f"Failed to analyze text: {response.text}")
            print(f"Text {text_id} has been analyzed for the first time")
        
        # Skip verification and voice generation if aborted
        if pre_existing and is_analyzed and has_characters and action == "abort":
            return
        
        # Step 4: Verify analysis results
        response = client.get(f"/api/text/{text_id}")
        if response.status_code != 200:
            raise Exception(f"Failed to get updated text details: {response.text}")
            
        text_data = response.json()
        if not text_data["analyzed"]:
            raise Exception("Text was not properly analyzed")
        
        # Step 4.5: Generate voices for characters
        print(f"\n----- Generating voices for characters -----")
        # Get all characters for the text
        response = client.get(f"/api/character/text/{text_id}")
        if response.status_code != 200:
            raise Exception("Failed to retrieve characters")
            
        characters = response.json()
        
        # Skip voice generation and speech generation for combine_audio option
        if pre_existing and is_analyzed and has_characters and action == "combine_audio":
            pass
        # Skip voice generation for generate_bg_music option
        elif pre_existing and is_analyzed and has_characters and action == "generate_bg_music":
            pass
        else:
            # Generate a voice for each character
            for character in characters:
                # If regenerating and character already has provider_id, skip voice generation
                if pre_existing and is_analyzed and has_characters and action == "regenerate" and character.get('provider_id'):
                    print(f"Using existing voice for character: {character['name']}")
                    continue
                    
                print(f"Generating voice for character: {character['name']}")
                response = client.post(
                    f"/api/character/{character['id']}/voice",
                    json={
                        "text_id": text_id
                    }
                )
                if response.status_code != 200:
                    raise Exception(f"Failed to generate voice for character {character['id']}: {response.text}")
                
                response_data = response.json()
                if response_data.get("status") == "skipped":
                    print(f"Skipped voice generation for character: {character['name']} - {response_data.get('message')}")
        
        # Step 5: Generate speech audio for each segment
        # Skip speech generation for generate_bg_music and combine_audio options
        if pre_existing and is_analyzed and has_characters and (action == "generate_bg_music" or action == "combine_audio"):
            print(f"\n----- Using existing speech audio segments -----")
        else:
            print(f"\n----- Generating speech audio for segments -----")
            response = client.post(f"/api/audio/text/{text_id}/generate-segments")
            if response.status_code != 200:
                raise Exception(f"Failed to generate segment audio: {response.text}")
                
            segment_audio_data = response.json()
            
            # Add a delay to ensure all segment audio files are fully saved
            print(f"\n----- Waiting for segment audio files to be saved -----")
            time.sleep(3)  # Wait for 3 seconds to ensure files are saved

        # Step 5.5: Generate Background Music
        # Skip bg music generation for combine_audio option
        if pre_existing and is_analyzed and has_characters and action == "combine_audio":
            print(f"\n----- Using existing background music -----")
        else:
            print(f"\n----- Generating background music -----")
            db_session = None
            try:
                db_session = SessionLocal()
                prompt_success, prompt, music_success = process_background_music_for_text(db_session, text_id)
                if not music_success:
                    print(f"Warning: Background music generation failed or was skipped. Prompt success: {prompt_success}, Prompt: {prompt}")
                else:
                    print(f"Background music generated successfully. Prompt: {prompt}")
            except Exception as e:
                print(f"Error during background music generation: {str(e)}")
                print("Warning: Proceeding without background music.")
            finally:
                if db_session:
                    db_session.close()
        
        # Step 6: Generate and Export Final Audio (Speech Segments + Background Music)
        print(f"\n----- Generating and Exporting Final Audio -----")
        
        output_path = get_audio_output_path(text_id) # Final desired path
        target_output_dir = os.path.dirname(output_path) # Directory for export_final_audio
        # get_audio_output_path ensures target_output_dir exists

        db_session_export = None
        generated_audio_by_export_func = None
        try:
            db_session_export = SessionLocal()
            # export_final_audio will use its default bg_volume (0.1) and trailing_silence (0.0)
            generated_audio_by_export_func = export_final_audio(
                db=db_session_export, 
                text_id=text_id,
                output_dir=target_output_dir
            )
        except Exception as e:
            # This captures errors if export_final_audio raises them
            print(f"Error during final audio export process: {str(e)}")
            raise Exception(f"Final audio export failed: {str(e)}") from e # Re-raise to be caught by main try-except
        finally:
            if db_session_export:
                db_session_export.close()

        if not generated_audio_by_export_func or not os.path.exists(generated_audio_by_export_func):
            raise Exception(f"Final audio file was not generated by export_final_audio or path is invalid: {generated_audio_by_export_func}")
        
        # Move the generated file to the specific filename format/path expected by this script
        if generated_audio_by_export_func != output_path:
            shutil.move(generated_audio_by_export_func, output_path)
            print(f"Moved final audio from {generated_audio_by_export_func} to {output_path}")
        else:
            print(f"Final audio generated directly at {output_path}")

        # Step 7: Verify audio file is valid by checking file size
        file_size = os.path.getsize(output_path)
        if file_size <= 0:
            raise Exception("Generated final audio file is empty or invalid")
            
        print(f"\nSuccess! Generated final audio file with size: {file_size} bytes at {output_path}")
        
    except Exception as e:
        print(f"\nERROR: Process failed: {str(e)}")

# SessionLogger.start_session("test_end_to_end") # Commenting out pytest specific logging for now

if __name__ == "__main__":
    SessionLogger.start_session("interactive_e2e_script") # Start session for script run
    run_interactive_e2e_flow()
    print("\nInteractive E2E processing finished.") 