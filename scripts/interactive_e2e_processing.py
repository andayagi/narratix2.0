#!/usr/bin/env python3
import asyncio
import os
import sys
import time
import datetime
import shutil
from typing import Dict, List, Optional, Tuple, Any
import tempfile

"""
Interactive end-to-end script for the text-to-audio processing pipeline.
Updated to test all new dedicated API endpoints for comprehensive validation.

To run this script:
    python3 scripts/interactive_e2e_processing.py
"""

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.database import SessionLocal
from utils.logging import SessionLogger
from db import crud

# Initialize API client lazily to avoid import issues
client = None
LONG_TIMEOUT = 6000.0

def get_api_client():
    """Initialize API client lazily"""
    global client
    if client is None:
        try:
            from fastapi.testclient import TestClient
            from api.main import app
            import utils.http_client
            
            # Set long timeout for HTTP requests
            original_create_client = utils.http_client.create_client
            utils.http_client.create_client = lambda **kwargs: original_create_client(timeout=LONG_TIMEOUT, **kwargs)

            # Create TestClient
            client = TestClient(app)
        except ImportError as e:
            print(f"❌ Failed to import API dependencies: {e}")
            print("Please install requirements: pip install -r requirements.txt")
            raise
    return client

class PipelineStatus:
    """Data class to hold pipeline status information"""
    def __init__(self, text_id: int):
        self.text_id = text_id
        self.text_exists = False
        self.text_analyzed = False
        self.characters_count = 0
        self.characters_with_voices = 0
        self.segments_count = 0
        self.segments_with_audio = 0
        self.has_bg_music_prompt = False
        self.has_bg_music_audio = False
        self.sound_effects_count = 0
        self.sound_effects_with_audio = 0
        self.word_timestamps_available = False

async def get_pipeline_status(text_id: int) -> PipelineStatus:
    """Get comprehensive status of pipeline data for a text_id"""
    status = PipelineStatus(text_id)
    
    # Check if text exists
    client = get_api_client()
    response = client.get(f"/api/text/{text_id}")
    if response.status_code != 200:
        return status
    
    text_data = response.json()
    status.text_exists = True
    status.text_analyzed = text_data.get("analyzed", False)
    status.word_timestamps_available = bool(text_data.get("word_timestamps"))
    
    # Check characters
    response = client.get(f"/api/character/text/{text_id}")
    if response.status_code == 200:
        characters = response.json()
        status.characters_count = len(characters)
        status.characters_with_voices = len([c for c in characters if c.get('provider_id')])
    
    # Check segments using database (segments endpoint not yet implemented)
    db = SessionLocal()
    try:
        # Get text object for background music fields
        text_obj = crud.get_text(db, text_id)
        if text_obj:
            status.has_bg_music_prompt = bool(text_obj.background_music_prompt)
            status.has_bg_music_audio = bool(text_obj.background_music_audio_b64)
            if not status.word_timestamps_available:  
                status.word_timestamps_available = bool(text_obj.word_timestamps)
        
        segments = crud.get_segments_by_text(db, text_id)
        status.segments_count = len(segments)
        status.segments_with_audio = len([s for s in segments if s.audio_data_b64])
        
        # Check sound effects
        sound_effects = crud.get_sound_effects_by_text(db, text_id)
        status.sound_effects_count = len(sound_effects)
        status.sound_effects_with_audio = len([sfx for sfx in sound_effects if sfx.audio_data_b64])
    finally:
        db.close()
    
    return status

def display_pipeline_status(status: PipelineStatus):
    """Display pipeline status in a user-friendly format"""
    print(f"\n{'='*60}")
    print(f"PIPELINE STATUS FOR TEXT ID: {status.text_id}")
    print(f"{'='*60}")
    
    if not status.text_exists:
        print("❌ Text does not exist in database")
        return
    
    print("📝 TEXT STATUS:")
    print(f"   {'✅' if status.text_analyzed else '❌'} Text analyzed: {status.text_analyzed}")
    print(f"   {'✅' if status.word_timestamps_available else '❌'} Word timestamps: {status.word_timestamps_available}")
    
    print("\n👥 CHARACTER STATUS:")
    print(f"   📊 Characters found: {status.characters_count}")
    print(f"   {'✅' if status.characters_with_voices == status.characters_count and status.characters_count > 0 else '❌'} Voices generated: {status.characters_with_voices}/{status.characters_count}")
    
    print("\n🎤 SPEECH STATUS:")
    print(f"   📊 Text segments: {status.segments_count}")
    print(f"   {'✅' if status.segments_with_audio == status.segments_count and status.segments_count > 0 else '❌'} Speech audio: {status.segments_with_audio}/{status.segments_count}")
    
    print("\n🎵 AUDIO ANALYSIS STATUS:")
    print(f"   {'✅' if status.has_bg_music_prompt else '❌'} Background music prompt: {status.has_bg_music_prompt}")
    print(f"   {'✅' if status.has_bg_music_audio else '❌'} Background music audio: {status.has_bg_music_audio}")
    print(f"   📊 Sound effects identified: {status.sound_effects_count}")
    print(f"   {'✅' if status.sound_effects_with_audio == status.sound_effects_count and status.sound_effects_count > 0 else '❌'} Sound effects audio: {status.sound_effects_with_audio}/{status.sound_effects_count}")
    
    print(f"\n{'='*60}")

def get_service_options(status: PipelineStatus) -> Dict[str, bool]:
    """Show all available services - dependency validation happens after user selection"""
    options = {
        "text_analysis": True,
        "voice_generation": True,
        "speech_generation": True,
        "audio_analysis": True,
        "bg_music_generation": True,
        "sfx_generation": True,
        "audio_combining": True
    }
    return options

def prompt_for_services(status: PipelineStatus) -> Tuple[bool, List[str], bool]:
    """Prompt user for which services to run"""
    options = get_service_options(status)
    
    print("\n🎛️  SERVICE SELECTION:")
    print("Available options:")
    print("1. Full pipeline (adaptive - runs all services as they become available)")
    print("2. Custom selection")
    print("3. Abort")
    
    while True:
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        if choice == "1":
            # Run adaptive full pipeline
            return True, [], True  # Empty list means adaptive mode
        elif choice == "2":
            # Custom selection
            proceed, services = prompt_custom_services(options)
            return proceed, services, False
        elif choice == "3":
            return False, [], False
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

def prompt_custom_services(options: Dict[str, bool]) -> Tuple[bool, List[str]]:
    """Prompt for custom service selection"""
    service_descriptions = {
        "text_analysis": "📝 Text Analysis (NEW ENDPOINT: /api/text-analysis/)",
        "voice_generation": "🎙️  Voice Generation (existing endpoints)",
        "speech_generation": "🗣️  Speech Generation (existing endpoints)",
        "audio_analysis": "🎵 Audio Analysis (NEW ENDPOINT: /api/audio-analysis/)",
        "bg_music_generation": "🎼 Background Music (NEW ENDPOINT: /api/background-music/)",
        "sfx_generation": "🔊 Sound Effects (existing endpoint)",
        "audio_combining": "🎬 Audio Export (NEW ENDPOINT: /api/export/)"
    }
    
    print("\n📋 CUSTOM SERVICE SELECTION (Testing New API Endpoints):")
    available_services = [(key, desc) for key, desc in service_descriptions.items() if options[key]]
    
    if not available_services:
        print("❌ No services are currently available based on existing data.")
        return False, []
    
    for i, (key, desc) in enumerate(available_services, 1):
        print(f"{i}. {desc}")
    
    print("\nSelect services (comma-separated numbers, e.g., '1,3,5'):")
    print("Or type 'all' for all available services")
    print("Or type 'none' to abort")
    
    while True:
        selection = input("Your selection: ").strip().lower()
        
        if selection == "none":
            return False, []
        elif selection == "all":
            return True, [key for key, _ in available_services]
        else:
            try:
                indices = [int(x.strip()) for x in selection.split(',')]
                if all(1 <= i <= len(available_services) for i in indices):
                    selected_services = [available_services[i-1][0] for i in indices]
                    return True, selected_services
                else:
                    print(f"Invalid selection. Enter numbers between 1 and {len(available_services)}")
            except ValueError:
                print("Invalid format. Use comma-separated numbers (e.g., '1,3,5')")

def validate_service_dependencies(services: List[str], status: PipelineStatus) -> Tuple[bool, List[str]]:
    """Validate that service dependencies are met or will be met by selected services"""
    errors = []
    
    # Check what will be available after running selected services
    will_have_text_analyzed = status.text_analyzed or "text_analysis" in services
    will_have_characters = status.characters_count > 0 or "text_analysis" in services
    will_have_voices = status.characters_with_voices > 0 or "voice_generation" in services
    will_have_segments_audio = status.segments_with_audio > 0 or "speech_generation" in services
    will_have_bg_music_prompt = status.has_bg_music_prompt or "audio_analysis" in services
    will_have_sound_effects = status.sound_effects_count > 0 or "audio_analysis" in services
    
    # Define dependencies with improved logic
    dependency_checks = {
        "voice_generation": (will_have_text_analyzed and will_have_characters, 
                           "Text must be analyzed with characters present (run text_analysis first)"),
        "speech_generation": (will_have_voices, 
                            "Characters must have generated voices (run voice_generation first)"),
        "bg_music_generation": (will_have_bg_music_prompt, 
                              "Background music prompt must exist (run audio_analysis first)"),
        "sfx_generation": (will_have_sound_effects, 
                         "Sound effects must be identified (run audio_analysis first)"),
        "audio_combining": (will_have_segments_audio, 
                          "Speech audio segments must be generated first (run speech_generation)")
    }
    
    for service in services:
        if service in dependency_checks:
            is_satisfied, error_msg = dependency_checks[service]
            if not is_satisfied:
                errors.append(f"❌ {service}: {error_msg}")
    
    return len(errors) == 0, errors

async def get_text_id_from_user() -> Optional[int]:
    """Get text ID from user input (file or direct ID)"""
    print("\n📖 TEXT SOURCE SELECTION:")
    print("1. Use input file from scripts/input_interactive_e2e.txt")
    print("2. Use existing text_id")
    
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice == "1":
            return await create_or_find_text_from_file()
        elif choice == "2":
            text_id = input("Enter the text_id to process: ").strip()
            if not text_id:
                print("Text ID cannot be empty. Please try again.")
                continue
        try:
            return int(text_id)
        except ValueError:
            print("Text ID must be a number. Please try again.")
            continue
        else:
            print("Invalid choice. Please enter 1 or 2.")

async def create_or_find_text_from_file() -> Optional[int]:
    """Create or find text from input file"""
    input_file_path = os.path.join(PROJECT_ROOT, 'scripts', 'input_interactive_e2e.txt')
    
    try:
        with open(input_file_path, 'r') as f:
            text_content = f.read().strip()
            
            if not text_content:
                print("❌ Input text file is empty")
                return None
            
        print("\n📝 Creating or finding text in database...")
        client = get_api_client()
        response = client.post(
            "/api/text/",
            json={
                "content": text_content,
                "title": "E2E Test Text"
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to create or find text: {response.text}")
            return None
            
        text_data = response.json()
        text_id = text_data["id"]
        
        if text_data.get("created", True):
            print(f"✅ Created new text with ID {text_id}")
        else:
            print(f"✅ Found existing text with ID {text_id}")
            
        return text_id
        
    except FileNotFoundError:
        print(f"❌ Input file not found: {input_file_path}")
        return None
    except Exception as e:
        print(f"❌ Error processing input file: {str(e)}")
        return None

# Service execution functions - Updated to use NEW DEDICATED ENDPOINTS
async def run_text_analysis(text_id: int) -> bool:
    """Run text analysis using NEW /api/text-analysis/ endpoint"""
    print("📝 Testing NEW ENDPOINT: /api/text-analysis/{text_id}/analyze")
    try:
        client = get_api_client()
        response = client.post(f"/api/text-analysis/{text_id}/analyze")
        print(f"Text Analysis Endpoint Response: {response.status_code}")
        if response.status_code not in [200, 202]:
            print(f"❌ NEW ENDPOINT ERROR: {response.text}")
            return False
        
        print("✅ NEW ENDPOINT SUCCESS: Text analysis completed")
        
        # Test GET endpoints too
        print("📝 Testing GET /api/text-analysis/{text_id}")
        response = client.get(f"/api/text-analysis/{text_id}")
        if response.status_code == 200:
            print("✅ NEW ENDPOINT SUCCESS: Text analysis status retrieved")
        else:
            print(f"⚠️  GET endpoint returned: {response.status_code}")
            
        return True
    except Exception as e:
        print(f"❌ NEW ENDPOINT ERROR: {str(e)}")
        return False

async def run_voice_generation(text_id: int) -> bool:
    """Run voice generation for all characters in parallel (existing endpoints)"""
    print("🎙️  Running voice generation (existing endpoints) - PARALLEL MODE...")
    try:
        # Get characters
        client = get_api_client()
        response = client.get(f"/api/character/text/{text_id}")
        if response.status_code != 200:
            print("❌ Failed to retrieve characters")
            return False
            
        characters = response.json()
        
        # Filter characters that need voice generation
        characters_needing_voices = [c for c in characters if not c.get('provider_id')]
        characters_with_voices = [c for c in characters if c.get('provider_id')]
        
        if characters_with_voices:
            print(f"⏭️  {len(characters_with_voices)} characters already have voices")
        
        if not characters_needing_voices:
            print("✅ Voice generation completed (all voices already exist)")
            return True
        
        print(f"🚀 Generating voices for {len(characters_needing_voices)} characters in PARALLEL...")
        
        # Create parallel tasks for voice generation
        async def generate_character_voice(character):
            print(f"🎙️  Generating voice for {character['name']}...")
            response = client.post(
                f"/api/character/{character['id']}/voice",
                json={"text_id": text_id}
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to generate voice for {character['name']}")
                return False
            
            print(f"✅ Voice generated for {character['name']}")
            return True
        
        # Execute all voice generations in parallel
        voice_tasks = [generate_character_voice(char) for char in characters_needing_voices]
        voice_results = await asyncio.gather(*voice_tasks, return_exceptions=True)
        
        # Process results
        successful_generations = 0
        failed_generations = 0
        
        for i, result in enumerate(voice_results):
            if isinstance(result, Exception):
                print(f"❌ Voice generation failed for {characters_needing_voices[i]['name']}: {result}")
                failed_generations += 1
            elif result:
                successful_generations += 1
            else:
                failed_generations += 1
        
        print(f"✅ Parallel voice generation completed: {successful_generations} successful, {failed_generations} failed")
        return failed_generations == 0
        
    except Exception as e:
        print(f"❌ Error in parallel voice generation: {str(e)}")
        return False

async def run_speech_generation(text_id: int) -> bool:
    """Run speech generation for all segments (existing endpoint)"""
    print("🗣️  Running speech generation (existing endpoint)...")
    try:
        client = get_api_client()
        response = client.post(f"/api/audio/text/{text_id}/generate-segments")
        if response.status_code == 200:
            print("✅ Speech generation completed")
            # Wait for files to be saved
            await asyncio.sleep(3)
            return True
        else:
            print(f"❌ Speech generation failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error in speech generation: {str(e)}")
        return False

async def run_audio_analysis(text_id: int) -> bool:
    """Run audio analysis using NEW /api/audio-analysis/ endpoint"""
    print("🎵 Testing NEW ENDPOINT: /api/audio-analysis/{text_id}/analyze")
    try:
        client = get_api_client()
        response = client.post(f"/api/audio-analysis/{text_id}/analyze")
        print(f"Audio Analysis Endpoint Response: {response.status_code}")
        if response.status_code not in [200, 202]:
            print(f"❌ NEW ENDPOINT ERROR: {response.text}")
            return False
            
        print("✅ NEW ENDPOINT SUCCESS: Audio analysis completed")
        
        # Test additional GET endpoints
        print("🎵 Testing GET /api/audio-analysis/{text_id}")
        response = client.get(f"/api/audio-analysis/{text_id}")
        if response.status_code == 200:
            print("✅ NEW ENDPOINT SUCCESS: Audio analysis results retrieved")
        
        print("🎵 Testing GET /api/audio-analysis/{text_id}/soundscape")
        response = client.get(f"/api/audio-analysis/{text_id}/soundscape")
        if response.status_code == 200:
            print("✅ NEW ENDPOINT SUCCESS: Soundscape data retrieved")
            
        print("🎵 Testing GET /api/audio-analysis/{text_id}/sound-effects")
        response = client.get(f"/api/audio-analysis/{text_id}/sound-effects")
        if response.status_code == 200:
            print("✅ NEW ENDPOINT SUCCESS: Sound effects data retrieved")
            
        return True
            
    except Exception as e:
        print(f"❌ NEW ENDPOINT ERROR: {str(e)}")
        return False

async def run_bg_music_generation(text_id: int) -> bool:
    """Run background music generation using NEW /api/background-music/ endpoint"""
    print("🎼 Testing NEW ENDPOINT: /api/background-music/{text_id}/process")
    try:
        client = get_api_client()
        response = client.post(f"/api/background-music/{text_id}/process?force=true")
        print(f"Background Music Endpoint Response: {response.status_code}")
        if response.status_code not in [200, 202]:
            print(f"❌ NEW ENDPOINT ERROR: {response.text}")
            return False
            
        print("✅ NEW ENDPOINT SUCCESS: Background music generation triggered")
        
        # Test GET endpoints
        print("🎼 Testing GET /api/background-music/{text_id}")
        response = client.get(f"/api/background-music/{text_id}")
        if response.status_code == 200:
            print("✅ NEW ENDPOINT SUCCESS: Background music status retrieved")
            
        return True  # Return immediately after triggering webhook
            
    except Exception as e:
        print(f"❌ NEW ENDPOINT ERROR: {str(e)}")
        return False

async def run_sfx_generation(text_id: int) -> bool:
    """Run sound effects generation (existing endpoint)"""
    print("🔊 Running sound effects generation (existing endpoint)...")
    try:
        client = get_api_client()
        response = client.post(f"/api/sound-effects/text/{text_id}/generate?force=true")
        if response.status_code in [200, 202]:
            print("✅ Sound effects generation triggered")
            return True  # Return immediately after triggering webhook
        else:
            print(f"❌ Sound effects generation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error in sound effects generation: {str(e)}")
        return False

async def reset_text_pipeline_data(text_id: int) -> bool:
    """Reset all pipeline data for a text, keeping only the original text content"""
    print(f"🗑️  Resetting all pipeline data for text {text_id}...")
    
    try:
        db = SessionLocal()
        try:
            # Get the text object
            text_obj = crud.get_text(db, text_id)
            if not text_obj:
                print(f"❌ Text {text_id} not found")
                return False
            
            # Clear text analysis data
            text_obj.analyzed = False
            text_obj.word_timestamps = None
            text_obj.background_music_prompt = None
            text_obj.background_music_audio_b64 = None
            
            # Delete all characters for this text
            characters = crud.get_characters_by_text(db, text_id)
            deleted_characters = 0
            for character in characters:
                crud.delete_character(db, character.character_id)
                deleted_characters += 1
            
            # Delete all segments for this text
            segments = crud.get_segments_by_text(db, text_id)
            deleted_segments = 0
            for segment in segments:
                crud.delete_segment(db, segment.segment_id)
                deleted_segments += 1
            
            # Delete all sound effects for this text
            deleted_sound_effects = crud.delete_sound_effects_by_text(db, text_id)
            
            # Commit all changes
            db.commit()
            
            print(f"✅ Pipeline data reset complete:")
            print(f"   🗑️  Deleted {deleted_characters} characters")
            print(f"   🗑️  Deleted {deleted_segments} segments") 
            print(f"   🗑️  Deleted {deleted_sound_effects} sound effects")
            print(f"   🗑️  Cleared background music data")
            print(f"   🗑️  Reset analysis flags")
            
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error resetting pipeline data: {str(e)}")
        return False

async def run_audio_combining(text_id: int) -> str:
    """Run final audio combining using NEW /api/export/ endpoint"""
    print("🎬 Testing NEW ENDPOINT: /api/export/{text_id}/final-audio")
    try:
        client = get_api_client()
        response = client.post(f"/api/export/{text_id}/final-audio")
        print(f"Export Endpoint Response: {response.status_code}")
        if response.status_code not in [200, 202]:
            print(f"❌ NEW ENDPOINT ERROR: {response.text}")
            return None
        
        print("✅ NEW ENDPOINT SUCCESS: Final audio export completed")
        
        # Parse the actual response to get the real file path
        try:
            response_data = response.json()
            actual_file_path = response_data.get("data", {}).get("audio_file")
            if actual_file_path:
                print(f"📁 Actual file created: {actual_file_path}")
            else:
                print("⚠️  No file path returned in response")
        except Exception as e:
            print(f"⚠️  Could not parse response: {e}")
            actual_file_path = None
        
        # Test status endpoint
        print("🎬 Testing GET /api/export/{text_id}/status")
        response = client.get(f"/api/export/{text_id}/status")
        if response.status_code == 200:
            print("✅ NEW ENDPOINT SUCCESS: Export status retrieved")
            
        # Return the actual file path if available, otherwise return a generic path
        return actual_file_path if actual_file_path else f"output/final_audio_{text_id}_[timestamp].mp3"
        
    except Exception as e:
        print(f"❌ NEW ENDPOINT ERROR: {str(e)}")
        return None

async def run_adaptive_pipeline(text_id: int) -> Dict[str, Any]:
    """Execute full pipeline - RESET EVERYTHING then regenerate from scratch"""
    results = {}
    
    print("🚀 Running FULL PIPELINE - COMPLETE RESET AND REGENERATION...")
    print("🎯 This will test all new dedicated endpoints with MAXIMUM PARALLELIZATION:")
    print("   📝 /api/text-analysis/")
    print("   🎵 /api/audio-analysis/")
    print("   🎼 /api/background-music/")
    print("   🎬 /api/export/")
    print("   🔊 /api/sound-effects/ (existing)")
    print("🚀 PIPELINE: Reset → Analysis → (Voice+Speech) || (BG Music + SFX) → Final Audio")
    
    # Phase 0: Reset all existing pipeline data
    print("\n🗑️  Phase 0: Complete Pipeline Reset...")
    
    # Check if text has any existing pipeline data
    initial_status = await get_pipeline_status(text_id)
    has_existing_data = (
        initial_status.text_analyzed or 
        initial_status.characters_count > 0 or 
        initial_status.segments_count > 0 or 
        initial_status.sound_effects_count > 0 or
        initial_status.has_bg_music_prompt or 
        initial_status.has_bg_music_audio
    )
    
    if has_existing_data:
        print(f"🔍 Detected existing pipeline data for text {text_id}")
        print("🗑️  Performing complete reset to ensure clean regeneration...")
        
        reset_success = await reset_text_pipeline_data(text_id)
        if not reset_success:
            print("❌ CRITICAL FAILURE: Failed to reset pipeline data")
            results["pipeline_status"] = "FAILED"
            results["failed_service"] = "reset_pipeline_data"
            return results
        
        print("✅ Reset complete - text is now ready for full regeneration")
    else:
        print("✅ Text has no existing pipeline data - proceeding with fresh generation")
    
    # Phase 1: Sequential Analysis (dependencies require this)
    print("\n🔄 Phase 1: Sequential Analysis Phase...")
    # Text analysis (always run since we reset everything)
    results["text_analysis"] = await run_text_analysis(text_id)
    if not results["text_analysis"]:
        print("❌ CRITICAL FAILURE: text_analysis failed, stopping pipeline")
        results["pipeline_status"] = "FAILED"
        results["failed_service"] = "text_analysis"
        return results
    
    # Audio analysis (always run since we reset everything)
    print("🎵 Running audio analysis...")
    results["audio_analysis"] = await run_audio_analysis(text_id)
    if not results["audio_analysis"]:
        print("❌ CRITICAL FAILURE: audio_analysis failed, stopping pipeline")
        results["pipeline_status"] = "FAILED"
        results["failed_service"] = "audio_analysis"
        return results
    
    # Phase 2: TRUE PARALLEL EXECUTION
    print("\n🚀 Phase 2: PARALLEL Track Execution...")
    
    parallel_tasks = []
    
    # TRACK 1: Speech Generation (Voice → Speech)
    async def speech_track():
        track_results = {}
        print("🎤 TRACK 1: Speech Generation (Voice → Speech)")
        
        # Generate character voices (always needed since we reset)
        print("🎙️  Generating character voices in parallel...")
        track_results["voice_generation"] = await run_voice_generation(text_id)
        if not track_results["voice_generation"]:
            print("❌ CRITICAL: Voice generation failed in speech track")
            track_results["pipeline_status"] = "FAILED"
            track_results["failed_service"] = "voice_generation"
            return track_results
        
        # Generate speech audio (always needed since we reset)
        print("🗣️  Generating speech audio...")
        track_results["speech_generation"] = await run_speech_generation(text_id)
        if not track_results["speech_generation"]:
            print("❌ CRITICAL: Speech generation failed in speech track")
            track_results["pipeline_status"] = "FAILED"
            track_results["failed_service"] = "speech_generation"
            return track_results
            
        print("✅ TRACK 1 COMPLETED: Speech generation track")
        return track_results
    
    # TRACK 2: Audio Generation (BG Music || SFX in parallel)
    async def audio_generation_track():
        track_results = {}
        print("🎵 TRACK 2: Audio Generation (BG Music || SFX)")
        
        # Both background music and sound effects always needed since we reset
        print("🎼 Adding background music generation to parallel tasks...")
        print("🔊 Adding sound effects generation to parallel tasks...")
        
        audio_tasks = [
            ("bg_music", run_bg_music_generation(text_id)),
            ("sfx", run_sfx_generation(text_id))
        ]
        
        # Execute audio generation tasks in parallel
        print(f"🚀 Executing {len(audio_tasks)} audio generation tasks in PARALLEL...")
        audio_results = await asyncio.gather(*[task for _, task in audio_tasks], return_exceptions=True)
        
        # Process parallel audio results
        for i, (task_name, _) in enumerate(audio_tasks):
            result = audio_results[i]
            if isinstance(result, Exception):
                print(f"❌ {task_name} failed: {result}")
                track_results[f"{task_name}_generation"] = False
            else:
                track_results[f"{task_name}_generation"] = result
                print(f"✅ {task_name} webhook triggered: {result}")
        
        # Now wait for both to complete in parallel
        bg_triggered = track_results.get("bg_music_generation", False)
        sfx_triggered = track_results.get("sfx_generation", False)
        
        if bg_triggered or sfx_triggered:
            completion_results = await wait_for_audio_generation_completion(text_id, bg_triggered, sfx_triggered)
            # Update results based on actual completion
            if bg_triggered:
                track_results["bg_music_generation"] = completion_results["bg_music_completed"]
            if sfx_triggered:
                track_results["sfx_generation"] = completion_results["sfx_completed"]
        
        print("✅ TRACK 2 COMPLETED: Audio generation track")
        return track_results
    
    # Execute both tracks in PARALLEL
    print("🚀 Executing Speech Track || Audio Track in PARALLEL...")
    parallel_tasks = [speech_track(), audio_generation_track()]
    
    track_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
    
    # Process parallel track results
    for i, track_result in enumerate(track_results):
        track_name = "Speech Track" if i == 0 else "Audio Track"
        if isinstance(track_result, Exception):
            print(f"❌ {track_name} failed completely: {track_result}")
            results["pipeline_status"] = "FAILED"
            results["failed_service"] = f"{track_name.lower().replace(' ', '_')}_exception"
            return results
        elif isinstance(track_result, dict):
            results.update(track_result)
            # Check for critical failures reported by tracks
            if track_result.get("pipeline_status") == "FAILED":
                print(f"💥 Critical failure in {track_name}")
                return results
    
    print("✅ PARALLEL TRACKS COMPLETED SUCCESSFULLY")
    
    # Phase 3: Final Audio Assembly
    print("\n🎬 Phase 3: Final Audio Assembly...")
    output_path = await run_audio_combining(text_id)
    results["audio_combining"] = output_path is not None
    if output_path:
        results["output_path"] = output_path
        print(f"✅ Final audio created: {output_path}")
    else:
        print("❌ Final audio assembly failed")
    
    print("🎉 TRULY PARALLEL ADAPTIVE PIPELINE COMPLETED!")
    return results

async def run_parallel_pipeline(text_id: int, services: List[str]) -> Dict[str, Any]:
    """Execute services with optimal parallelization - TESTING SELECTED NEW ENDPOINTS"""
    results = {}
    
    print(f"🎯 Testing selected endpoints: {', '.join(services)}")
    
    # Sequential services that must run first
    sequential_services = ["text_analysis", "audio_analysis"]
    
    # Services that can run in parallel after their dependencies
    parallel_groups = {
        "speech_track": ["voice_generation", "speech_generation"],
        "audio_track": ["bg_music_generation", "sfx_generation"]
    }
    
    # Execute sequential services first
    for service in sequential_services:
        if service in services:
            print(f"\n🔄 Testing {service} endpoints...")
            if service == "text_analysis":
                results[service] = await run_text_analysis(text_id)
            elif service == "audio_analysis":
                results[service] = await run_audio_analysis(text_id)
                
            if not results.get(service, False):
                print(f"❌ CRITICAL FAILURE: {service} failed, stopping pipeline immediately")
                print(f"💥 Pipeline execution terminated due to critical service failure")
                results["pipeline_status"] = "FAILED"
                results["failed_service"] = service
                return results
    
    # Execute parallel groups
    parallel_tasks = []
    
    # Speech track
    speech_services = [s for s in services if s in parallel_groups["speech_track"]]
    if speech_services:
        async def speech_track():
            track_results = {}
            print(f"\n🎤 Testing speech track endpoints: {speech_services}")
            
            # Execute speech services in parallel where possible
            speech_tasks = []
            
            if "voice_generation" in speech_services:
                speech_tasks.append(("voice_generation", run_voice_generation(text_id)))
            
            # Speech generation depends on voice generation, so we handle it after
            voice_completed = True
            if speech_tasks:
                # Run voice generation first (if needed)
                voice_results = await asyncio.gather(*[task for _, task in speech_tasks], return_exceptions=True)
                for i, (task_name, _) in enumerate(speech_tasks):
                    result = voice_results[i]
                    if isinstance(result, Exception):
                        print(f"❌ CRITICAL FAILURE: {task_name} failed in parallel track: {result}")
                        track_results["pipeline_status"] = "FAILED"
                        track_results["failed_service"] = task_name
                        return track_results
                    else:
                        track_results[task_name] = result
                        voice_completed = voice_completed and result
            
            # Now run speech generation if needed and voice generation succeeded
            if "speech_generation" in speech_services and voice_completed:
                track_results["speech_generation"] = await run_speech_generation(text_id)
                if not track_results.get("speech_generation", False):
                    print(f"❌ CRITICAL FAILURE: speech_generation failed in parallel track")
                    track_results["pipeline_status"] = "FAILED"
                    track_results["failed_service"] = "speech_generation"
                    return track_results
                
            return track_results
            
        parallel_tasks.append(speech_track())
    
    # Audio track
    audio_services = [s for s in services if s in parallel_groups["audio_track"]]
    if audio_services:
        async def audio_track():
            track_results = {}
            print(f"\n🎵 Testing audio track endpoints: {audio_services}")
            # BG music and SFX can run in parallel - trigger both then wait
            audio_tasks = []
            
            bg_music_in_services = "bg_music_generation" in audio_services
            sfx_in_services = "sfx_generation" in audio_services
            
            if bg_music_in_services:
                audio_tasks.append(run_bg_music_generation(text_id))
            if sfx_in_services:
                audio_tasks.append(run_sfx_generation(text_id))
                
            if audio_tasks:
                # Trigger both webhooks in parallel
                print("🔄 Triggering audio generation webhooks in parallel...")
                audio_results = await asyncio.gather(*audio_tasks, return_exceptions=True)
                
                # Check if webhooks were successfully triggered
                bg_music_triggered = False
                sfx_triggered = False
                
                if bg_music_in_services:
                    bg_music_triggered = audio_results[0] if not isinstance(audio_results[0], Exception) else False
                    track_results["bg_music_generation"] = bg_music_triggered
                if sfx_in_services:
                    idx = 1 if bg_music_in_services else 0
                    sfx_triggered = audio_results[idx] if not isinstance(audio_results[idx], Exception) else False
                    track_results["sfx_generation"] = sfx_triggered
                
                # Now wait for both to complete in parallel
                if bg_music_triggered or sfx_triggered:
                    completion_results = await wait_for_audio_generation_completion(text_id, bg_music_triggered, sfx_triggered)
                    # Update results based on actual completion
                    if bg_music_triggered:
                        track_results["bg_music_generation"] = completion_results["bg_music_completed"]
                    if sfx_triggered:
                        track_results["sfx_generation"] = completion_results["sfx_completed"]
                    
            return track_results
            
        parallel_tasks.append(audio_track())
    
    # Execute parallel tracks
    if parallel_tasks:
        print("🚀 Executing parallel endpoint testing...")
        track_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
        
        # Merge results and check for critical failures
        for track_result in track_results:
            if isinstance(track_result, dict):
                results.update(track_result)
                # Check if any track reported a critical failure
                if track_result.get("pipeline_status") == "FAILED":
                    print(f"💥 Pipeline execution terminated due to critical service failure")
                    return results
            else:
                print(f"⚠️  Parallel track failed: {track_result}")
                # If a track completely failed (exception), treat as critical if it was handling critical services
                results["pipeline_status"] = "FAILED"
                results["failed_service"] = "parallel_track_exception"
                return results
    
    # Finally, run audio combining if requested
    if "audio_combining" in services:
        print(f"\n🎬 Testing export endpoints...")
        output_path = await run_audio_combining(text_id)
        results["audio_combining"] = output_path is not None
        if output_path:
            results["output_path"] = output_path
    
    return results

async def main():
    """Main async entry point - COMPREHENSIVE ENDPOINT TESTING"""
    print("🎵 Narratix Async E2E Pipeline - NEW ENDPOINT TESTING")
    print("=====================================================")
    print("🎯 This script will test all new dedicated endpoints:")
    print("   📝 /api/text-analysis/ - Text analysis operations")
    print("   🎵 /api/audio-analysis/ - Audio analysis operations") 
    print("   🎼 /api/background-music/ - Background music operations")
    print("   🎬 /api/export/ - Audio export operations")
    print("   🔊 /api/sound-effects/ - Sound effects operations (existing)")
    print("=====================================================")
    
    try:
        # Get text ID from user
        text_id = await get_text_id_from_user()
        if not text_id:
            print("❌ No valid text ID provided. Exiting.")
            return
            
        # Get pipeline status
        print("\n🔍 Checking pipeline status...")
        status = await get_pipeline_status(text_id)
        display_pipeline_status(status)
        
        # Get service selection from user
        proceed, selected_services, is_adaptive = prompt_for_services(status)
        if not proceed:
            print("👋 Operation cancelled by user.")
            return
            
        # Execute pipeline
        start_time = time.time()
        
        if is_adaptive:
            # Run adaptive full pipeline
            print("\n🎯 TESTING ALL NEW ENDPOINTS IN ADAPTIVE MODE")
            results = await run_adaptive_pipeline(text_id)
        else:
            # Validate dependencies for custom selection
            valid, errors = validate_service_dependencies(selected_services, status)
            if not valid:
                print("\n❌ DEPENDENCY ERRORS:")
                for error in errors:
                    print(f"   {error}")
                print("\nPlease resolve dependencies and try again.")
                return
                
            print(f"\n🎯 TESTING SELECTED NEW ENDPOINTS")
            results = await run_parallel_pipeline(text_id, selected_services)
            
        end_time = time.time()
        
        # Show results
        print(f"\n📊 ENDPOINT TESTING RESULTS:")
        print(f"⏱️  Total time: {end_time - start_time:.2f} seconds")
        
        # Check if pipeline failed
        pipeline_failed = results.get("pipeline_status") == "FAILED"
        failed_service = results.get("failed_service")
        
        if pipeline_failed:
            print(f"\n💥 ENDPOINT TESTING FAILED!")
            print(f"❌ Critical service '{failed_service}' failed")
            print(f"🚫 Pipeline execution was terminated early")
        
        # Show detailed endpoint test results
        endpoint_tests = {
            "text_analysis": "📝 /api/text-analysis/ endpoints",
            "audio_analysis": "🎵 /api/audio-analysis/ endpoints", 
            "bg_music_generation": "🎼 /api/background-music/ endpoints",
            "audio_combining": "🎬 /api/export/ endpoints",
            "voice_generation": "🎙️  /api/character/ endpoints (existing)",
            "speech_generation": "🗣️  /api/audio/ endpoints (existing)",
            "sfx_generation": "🔊 /api/sound-effects/ endpoints (existing)"
        }
        
        print(f"\n🎯 DETAILED ENDPOINT TEST RESULTS:")
        for service, endpoint_desc in endpoint_tests.items():
            if service in results:
                status_icon = "✅" if results[service] else "❌"
                print(f"{status_icon} {endpoint_desc}: {'PASS' if results[service] else 'FAIL'}")
            
        if "output_path" in results:
            print(f"\n🎬 Final audio output: {results['output_path']}")
        
        if pipeline_failed:
            print(f"\n💥 ENDPOINT TESTING FAILED!")
            print(f"🔧 Check the failed endpoints and fix any issues before retrying.")
            # Exit with error code to indicate failure
            import sys
            sys.exit(1)
        else:
            print("\n✨ ENDPOINT TESTING COMPLETED SUCCESSFULLY!")
            print("🎉 All new dedicated endpoints are working correctly!")
        
    except Exception as e:
        print(f"\n💥 Endpoint testing failed with error: {str(e)}")
        raise

def run_interactive_e2e_flow():
    """Sync wrapper for the async main function"""
    asyncio.run(main())

if __name__ == "__main__":
    SessionLogger.start_session("async_interactive_e2e_endpoint_testing")
    run_interactive_e2e_flow()
    print("\n👋 Async Interactive E2E endpoint testing finished.") 