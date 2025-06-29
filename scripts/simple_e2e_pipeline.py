#!/usr/bin/env python3
import asyncio
import os
import sys
import time
import subprocess
import requests
import signal
from typing import Optional, Dict, Any

"""
Simple end-to-end pipeline script for text-to-audio processing.
Runs the complete pipeline with parallel optimization.

Usage:
    python3 scripts/simple_e2e_pipeline.py [text_id]
    
If no text_id provided, uses input_interactive_e2e.txt
"""

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.database import SessionLocal
from db import crud

# Initialize API client
client = None
server_process = None
LONG_TIMEOUT = 6000.0
SERVER_PORT = 8000
SERVER_HOST = "127.0.0.1"

def check_server_running() -> bool:
    """Check if FastAPI server is running"""
    try:
        response = requests.get(f"http://{SERVER_HOST}:{SERVER_PORT}/docs", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def start_server() -> bool:
    """Start the FastAPI server"""
    global server_process
    print("🚀 Starting FastAPI server...")
    
    try:
        # Start server using uvicorn
        server_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "api.main:app", 
            "--host", SERVER_HOST,
            "--port", str(SERVER_PORT),
            "--reload"
        ], cwd=PROJECT_ROOT)
        
        # Wait for server to start
        for i in range(30):  # Wait up to 30 seconds
            if check_server_running():
                print(f"✅ FastAPI server started on http://{SERVER_HOST}:{SERVER_PORT}")
                return True
            time.sleep(1)
            print(f"⏳ Waiting for server to start... ({i+1}/30)")
        
        print("❌ Server failed to start within 30 seconds")
        return False
        
    except Exception as e:
        print(f"❌ Failed to start server: {str(e)}")
        return False

def ensure_server_running() -> bool:
    """Ensure FastAPI server is running, start if needed"""
    if check_server_running():
        print(f"✅ FastAPI server already running on http://{SERVER_HOST}:{SERVER_PORT}")
        return True
    else:
        print("⚠️  FastAPI server not running, starting it...")
        return start_server()

def cleanup_server():
    """Clean up server process on exit"""
    global server_process
    if server_process:
        print("🛑 Stopping FastAPI server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        server_process = None

def get_api_client():
    """Initialize API client lazily"""
    global client
    if client is None:
        from fastapi.testclient import TestClient
        from api.main import app
        import utils.http_client
        
        # Set long timeout for HTTP requests
        original_create_client = utils.http_client.create_client
        utils.http_client.create_client = lambda **kwargs: original_create_client(timeout=LONG_TIMEOUT, **kwargs)
        client = TestClient(app)
    return client

async def get_or_create_text(text_id: Optional[int] = None) -> Optional[int]:
    """Get text_id from parameter or create from input file"""
    if text_id:
        # Validate existing text_id
        client = get_api_client()
        response = client.get(f"/api/text/{text_id}")
        if response.status_code == 200:
            print(f"✅ Using existing text_id: {text_id}")
            return text_id
        else:
            print(f"❌ Text ID {text_id} not found")
            return None
    
    # Create from input file
    input_file_path = os.path.join(PROJECT_ROOT, 'scripts', 'input_interactive_e2e.txt')
    try:
        with open(input_file_path, 'r') as f:
            text_content = f.read().strip()
            
        if not text_content:
            print("❌ Input text file is empty")
            return None
        
        print("📝 Creating text from input file...")
        client = get_api_client()
        response = client.post(
            "/api/text/",
            json={
                "content": text_content,
                "title": "Simple E2E Pipeline"
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to create text: {response.text}")
            return None
            
        text_data = response.json()
        text_id = text_data["id"]
        print(f"✅ Created text with ID: {text_id}")
        return text_id
        
    except FileNotFoundError:
        print(f"❌ Input file not found: {input_file_path}")
        return None
    except Exception as e:
        print(f"❌ Error processing input file: {str(e)}")
        return None

async def reset_pipeline_data(text_id: int) -> bool:
    """Reset all pipeline data for the text"""
    print(f"🗑️  Resetting pipeline data for text {text_id}...")
    
    try:
        db = SessionLocal()
        try:
            text_obj = crud.get_text(db, text_id)
            if not text_obj:
                print(f"❌ Text {text_id} not found")
                return False
            
            # Clear text analysis data
            text_obj.analyzed = False
            text_obj.word_timestamps = None
            text_obj.background_music_prompt = None
            text_obj.background_music_audio_b64 = None
            
            # Delete all related data
            deleted_characters = crud.delete_characters_by_text(db, text_id)
            deleted_segments = crud.delete_segments_by_text(db, text_id)
            deleted_sound_effects = crud.delete_sound_effects_by_text(db, text_id)
            
            db.commit()
            
            print(f"✅ Reset complete: {deleted_characters} characters, {deleted_segments} segments, {deleted_sound_effects} sound effects")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error resetting pipeline data: {str(e)}")
        return False

# Pipeline service functions
async def run_text_analysis(text_id: int) -> bool:
    """Run text analysis"""
    print("📝 Running text analysis...")
    try:
        client = get_api_client()
        response = client.post(f"/api/text-analysis/{text_id}/analyze")
        if response.status_code in [200, 202]:
            print("✅ Text analysis completed")
            return True
        else:
            print(f"❌ Text analysis failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Text analysis error: {str(e)}")
        return False

async def run_voice_generation(text_id: int) -> bool:
    """Run voice generation in parallel for all characters"""
    print("🎙️  Running voice generation...")
    try:
        client = get_api_client()
        response = client.get(f"/api/character/text/{text_id}")
        if response.status_code != 200:
            print("❌ Failed to retrieve characters")
            return False
            
        characters = response.json()
        characters_needing_voices = [c for c in characters if not c.get('provider_id')]
        
        if not characters_needing_voices:
            print("✅ All characters already have voices")
            return True
        
        print(f"🚀 Generating voices for {len(characters_needing_voices)} characters in parallel...")
        
        async def generate_voice(character):
            response = client.post(
                f"/api/character/{character['id']}/voice",
                json={"text_id": text_id}
            )
            success = response.status_code == 200
            print(f"{'✅' if success else '❌'} Voice for {character['name']}: {'Success' if success else 'Failed'}")
            return success
        
        # Execute all voice generations in parallel
        results = await asyncio.gather(*[generate_voice(char) for char in characters_needing_voices])
        success_count = sum(results)
        
        print(f"✅ Voice generation: {success_count}/{len(characters_needing_voices)} successful")
        return success_count == len(characters_needing_voices)
        
    except Exception as e:
        print(f"❌ Voice generation error: {str(e)}")
        return False

async def run_speech_generation(text_id: int) -> bool:
    """Run speech generation"""
    print("🗣️  Running speech generation...")
    try:
        client = get_api_client()
        response = client.post(f"/api/audio/text/{text_id}/generate-segments")
        if response.status_code == 200:
            print("✅ Speech generation completed")
            await asyncio.sleep(3)  # Wait for files to be saved
            return True
        else:
            print(f"❌ Speech generation failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Speech generation error: {str(e)}")
        return False

async def run_audio_analysis(text_id: int) -> bool:
    """Run audio analysis"""
    print("🎵 Running audio analysis...")
    try:
        client = get_api_client()
        response = client.post(f"/api/audio-analysis/{text_id}/analyze")
        if response.status_code in [200, 202]:
            print("✅ Audio analysis completed")
            return True
        else:
            print(f"❌ Audio analysis failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Audio analysis error: {str(e)}")
        return False

async def run_bg_music_generation(text_id: int) -> bool:
    """Run background music generation"""
    print("🎼 Running background music generation...")
    try:
        client = get_api_client()
        response = client.post(f"/api/background-music/{text_id}/process?force=true")
        if response.status_code in [200, 202]:
            print("✅ Background music generation triggered")
            return True
        else:
            print(f"❌ Background music generation failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Background music generation error: {str(e)}")
        return False

async def run_sfx_generation(text_id: int) -> bool:
    """Run sound effects generation"""
    print("🔊 Running sound effects generation...")
    try:
        client = get_api_client()
        response = client.post(f"/api/sound-effects/text/{text_id}/generate?force=true")
        if response.status_code in [200, 202]:
            print("✅ Sound effects generation triggered")
            return True
        else:
            print(f"❌ Sound effects generation failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Sound effects generation error: {str(e)}")
        return False

async def wait_for_audio_completion(text_id: int, bg_music: bool, sfx: bool, max_wait: int = 300) -> Dict[str, bool]:
    """Wait for background music and sound effects to complete"""
    print("⏳ Waiting for audio generation to complete...")
    
    db = SessionLocal()
    start_time = time.time()
    
    try:
        while time.time() - start_time < max_wait:
            # Check background music
            bg_complete = True
            if bg_music:
                text_obj = crud.get_text(db, text_id)
                bg_complete = bool(text_obj.background_music_audio_b64) if text_obj else False
            
            # Check sound effects
            sfx_complete = True
            if sfx:
                sound_effects = crud.get_sound_effects_by_text(db, text_id)
                sfx_complete = all(sfx.audio_data_b64 for sfx in sound_effects) if sound_effects else False
            
            if bg_complete and sfx_complete:
                print("✅ Audio generation completed")
                return {"bg_music_completed": bg_complete, "sfx_completed": sfx_complete}
            
            await asyncio.sleep(5)
            print(f"⏳ Still waiting... (BG: {'✅' if bg_complete else '⏳'}, SFX: {'✅' if sfx_complete else '⏳'})")
        
        print("⚠️  Audio generation timeout reached")
        return {"bg_music_completed": False, "sfx_completed": False}
        
    finally:
        db.close()

async def run_final_audio(text_id: int) -> Optional[str]:
    """Run final audio combining"""
    print("🎬 Running final audio export...")
    try:
        client = get_api_client()
        response = client.post(f"/api/export/{text_id}/final-audio")
        if response.status_code in [200, 202]:
            try:
                response_data = response.json()
                output_path = response_data.get("data", {}).get("audio_file")
                print(f"✅ Final audio export completed: {output_path}")
                return output_path
            except:
                print("✅ Final audio export completed")
                return f"output/final_audio_{text_id}.mp3"
        else:
            print(f"❌ Final audio export failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Final audio export error: {str(e)}")
        return None

async def run_pipeline(text_id: int) -> Dict[str, Any]:
    """Run the complete parallel pipeline"""
    print(f"\n🚀 Starting complete pipeline for text {text_id}")
    print("🎯 Pipeline structure:")
    print("   Track 1: Text Analysis → Voice Generation → Speech Generation")
    print("   Track 2: Audio Analysis → (Background Music || Sound Effects)")
    print("   Final: Audio Export")
    
    results = {}
    start_time = time.time()
    
    # Step 1: Reset all data
    if not await reset_pipeline_data(text_id):
        results["status"] = "FAILED"
        results["error"] = "Failed to reset pipeline data"
        return results
    
    # Step 2: Run parallel tracks
    async def speech_track():
        """Track 1: Text → Voice → Speech"""
        print("\n🎤 Starting Speech Track...")
        
        # Text analysis
        if not await run_text_analysis(text_id):
            return {"speech_track": False, "error": "text_analysis_failed"}
        
        # Voice generation (parallel)
        if not await run_voice_generation(text_id):
            return {"speech_track": False, "error": "voice_generation_failed"}
        
        # Speech generation
        if not await run_speech_generation(text_id):
            return {"speech_track": False, "error": "speech_generation_failed"}
        
        print("✅ Speech Track completed")
        return {"speech_track": True}
    
    async def audio_track():
        """Track 2: Audio Analysis → (BG Music || SFX)"""
        print("\n🎵 Starting Audio Track...")
        
        # Audio analysis
        if not await run_audio_analysis(text_id):
            return {"audio_track": False, "error": "audio_analysis_failed"}
        
        # Parallel audio generation
        print("🚀 Running background music and sound effects in parallel...")
        bg_task = run_bg_music_generation(text_id)
        sfx_task = run_sfx_generation(text_id)
        
        bg_result, sfx_result = await asyncio.gather(bg_task, sfx_task)
        
        if bg_result or sfx_result:
            # Wait for completion
            completion_results = await wait_for_audio_completion(text_id, bg_result, sfx_result)
            final_bg = completion_results["bg_music_completed"] if bg_result else True
            final_sfx = completion_results["sfx_completed"] if sfx_result else True
            
            if final_bg and final_sfx:
                print("✅ Audio Track completed")
                return {"audio_track": True}
            else:
                return {"audio_track": False, "error": "audio_completion_failed"}
        else:
            return {"audio_track": False, "error": "audio_generation_failed"}
    
    # Run both tracks in parallel
    print("\n🚀 Running Speech Track || Audio Track in parallel...")
    track_results = await asyncio.gather(speech_track(), audio_track())
    
    # Process results
    speech_result, audio_result = track_results
    results.update(speech_result)
    results.update(audio_result)
    
    # Check if both tracks succeeded
    if not (speech_result.get("speech_track") and audio_result.get("audio_track")):
        results["status"] = "FAILED"
        results["error"] = f"Track failures: {speech_result.get('error', 'none')}, {audio_result.get('error', 'none')}"
        return results
    
    # Step 3: Final audio export
    print("\n🎬 Running final audio export...")
    output_path = await run_final_audio(text_id)
    
    # Final results
    end_time = time.time()
    results["status"] = "SUCCESS" if output_path else "PARTIAL_SUCCESS"
    results["duration"] = end_time - start_time
    results["output_path"] = output_path
    
    return results

async def main():
    """Main function"""
    print("🎵 Simple E2E Pipeline")
    print("=====================")
    
    # Setup cleanup handler
    def signal_handler(signum, frame):
        cleanup_server()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Ensure FastAPI server is running
        if not ensure_server_running():
            print("❌ Failed to start FastAPI server")
            return
        
        # Get text_id from command line or use input file
        text_id_arg = sys.argv[1] if len(sys.argv) > 1 else None
        try:
            text_id_input = int(text_id_arg) if text_id_arg else None
        except ValueError:
            print(f"❌ Invalid text_id: {text_id_arg}")
            return
        
        # Get or create text
        text_id = await get_or_create_text(text_id_input)
        if not text_id:
            print("❌ Failed to get text_id")
            return
        
        # Run pipeline
        results = await run_pipeline(text_id)
        
        # Show results
        print(f"\n📊 PIPELINE RESULTS")
        print(f"===================")
        print(f"Status: {results['status']}")
        print(f"Duration: {results.get('duration', 0):.2f} seconds")
        
        if results.get("output_path"):
            print(f"Output: {results['output_path']}")
        
        if results.get("error"):
            print(f"Error: {results['error']}")
            sys.exit(1)
        
        print("\n✨ Pipeline completed successfully!")
        
    finally:
        # Always cleanup server on exit
        cleanup_server()

if __name__ == "__main__":
    asyncio.run(main()) 