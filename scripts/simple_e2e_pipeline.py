#!/usr/bin/env python3
import asyncio
import os
import sys
import time
import subprocess
import requests
import signal
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from contextlib import asynccontextmanager
import logging

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
from utils.ngrok_sync import smart_server_health_check
from services.replicate_audio import wait_for_webhook_completion_event, wait_for_sound_effects_completion_event

# Configuration
@dataclass
class PipelineConfig:
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    long_timeout: float = 6000.0
    server_startup_timeout: int = 30
    server_startup_check_interval: int = 1
    audio_completion_check_interval: int = 10
    audio_completion_progress_interval: int = 30
    audio_completion_max_wait: int = 600
    webhook_completion_timeout: int = 600
    post_speech_generation_wait: int = 3
    
    @property
    def base_url(self) -> str:
        return f"http://{self.server_host}:{self.server_port}"

config = PipelineConfig()

# Global state
server_process = None

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PipelineError(Exception):
    """Custom exception for pipeline errors"""
    pass

class ServerManager:
    """Manages FastAPI server lifecycle"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.process = None
    
    def is_running(self) -> bool:
        """Check if FastAPI server is running"""
        try:
            response = requests.get(f"{self.config.base_url}/docs", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def start(self) -> bool:
        """Start the FastAPI server"""
        print("🚀 Starting FastAPI server...")
        
        try:
            self.process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "api.main:app", 
                "--host", self.config.server_host,
                "--port", str(self.config.server_port),
                "--reload"
            ], cwd=PROJECT_ROOT)
            
            # Wait for server to start
            for i in range(self.config.server_startup_timeout):
                if smart_server_health_check():
                    print(f"✅ FastAPI server started and ngrok URL synced")
                    return True
                time.sleep(self.config.server_startup_check_interval)
                print(f"⏳ Waiting for server to start... ({i+1}/{self.config.server_startup_timeout})")
            
            print(f"❌ Server failed to start within {self.config.server_startup_timeout} seconds")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start server: {str(e)}")
            return False
    
    def ensure_running(self) -> bool:
        """Ensure FastAPI server is running, start if needed"""
        if smart_server_health_check():
            print(f"✅ FastAPI server already running (ngrok URL synced)")
            return True
        else:
            print("⚠️  FastAPI server not running, starting it...")
            return self.start()
    
    def cleanup(self):
        """Clean up server process"""
        if self.process:
            print("🛑 Stopping FastAPI server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

class APIClient:
    """Wrapper for HTTP API calls"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    @asynccontextmanager
    async def get_client(self):
        """Get async HTTP client with proper timeout"""
        async with httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=httpx.Timeout(self.config.long_timeout)
        ) as client:
            yield client
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make HTTP request with error handling"""
        async with self.get_client() as client:
            try:
                response = await getattr(client, method.lower())(endpoint, **kwargs)
                return response
            except Exception as e:
                logger.error(f"API request failed: {method} {endpoint} - {str(e)}")
                raise PipelineError(f"API request failed: {str(e)}")

class TextManager:
    """Manages text creation and retrieval"""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    async def get_or_create_text(self, text_id: Optional[int] = None) -> Optional[int]:
        """Get text_id from parameter or create from input file"""
        if text_id:
            return await self._validate_existing_text(text_id)
        return await self._create_from_input_file()
    
    async def _validate_existing_text(self, text_id: int) -> Optional[int]:
        """Validate existing text_id"""
        response = await self.api_client.make_request("GET", f"/api/text/{text_id}")
        if response.status_code == 200:
            print(f"✅ Using existing text_id: {text_id}")
            return text_id
        else:
            print(f"❌ Text ID {text_id} not found")
            return None
    
    async def _create_from_input_file(self) -> Optional[int]:
        """Create text from input file"""
        input_file_path = os.path.join(PROJECT_ROOT, 'scripts', 'input_interactive_e2e.txt')
        
        try:
            with open(input_file_path, 'r') as f:
                text_content = f.read().strip()
                
            if not text_content:
                print("❌ Input text file is empty")
                return None
            
            print("📝 Creating text from input file...")
            response = await self.api_client.make_request(
                "POST", "/api/text/",
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

class PipelineDataManager:
    """Manages pipeline data reset and cleanup"""
    
    async def reset_pipeline_data(self, text_id: int) -> bool:
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

class PipelineSteps:
    """Individual pipeline step implementations"""
    
    def __init__(self, api_client: APIClient, config: PipelineConfig):
        self.api_client = api_client
        self.config = config

    async def run_text_analysis(self, text_id: int) -> bool:
        """Run text analysis and wait for completion."""
        print("📝 Running text analysis...")
        try:
            # Start the analysis (non-blocking)
            start_response = await self.api_client.make_request(
                "POST", f"/api/text-analysis/{text_id}/analyze"
            )
            if start_response.status_code not in [200, 202]:
                print(f"❌ Text analysis failed to start: {start_response.text}")
                return False

            print("⏳ Text analysis started, waiting for completion...")

            # Poll for completion status
            max_wait = 120  # 2 minutes
            poll_interval = 5
            start_time = time.time()

            while time.time() - start_time < max_wait:
                await asyncio.sleep(poll_interval)
                status_response = await self.api_client.make_request(
                    "GET", f"/api/text/{text_id}"
                )
                
                if status_response.status_code == 200:
                    text_data = status_response.json()
                    if text_data.get("analyzed"):
                        print("✅ Text analysis completed")
                        return True
                
                elapsed = time.time() - start_time
                print(f"   ... still analyzing ({elapsed:.0f}s)")

            print("⏰ Timeout waiting for text analysis to complete")
            return False

        except Exception as e:
            print(f"❌ Text analysis error: {str(e)}")
            return False

    async def run_voice_generation(self, text_id: int) -> bool:
        """Run voice generation in parallel for all characters"""
        print("🎙️  Running voice generation...")
        try:
            response = await self.api_client.make_request("GET", f"/api/character/text/{text_id}")
            if response.status_code != 200:
                print("❌ Failed to retrieve characters")
                return False
                
            characters = response.json()
            characters_needing_voices = [c for c in characters if not c.get('provider_id')]
            
            print(f"📊 Voice status: {len(characters)} total characters, {len(characters_needing_voices)} need voices")
            for char in characters:
                has_voice = "✅" if char.get('provider_id') else "❌"
                print(f"   {has_voice} {char['name']}: {char.get('provider_id', 'No voice')}")
            
            if not characters_needing_voices:
                print("✅ All characters already have voices")
                return True
            
            print(f"🚀 Generating voices for {len(characters_needing_voices)} characters in parallel...")
            
            async def generate_voice(character):
                response = await self.api_client.make_request(
                    "POST", f"/api/character/{character['id']}/voice",
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

    async def run_speech_generation(self, text_id: int) -> bool:
        """Run speech generation"""
        print("🗣️  Running speech generation...")
        try:
            response = await self.api_client.make_request("POST", f"/api/audio/text/{text_id}/generate-segments")
            if response.status_code == 200:
                print("✅ Speech generation completed")
                await asyncio.sleep(self.config.post_speech_generation_wait)  # Wait for files to be saved
                return True
            else:
                print(f"❌ Speech generation failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Speech generation error: {str(e)}")
            return False

    async def run_audio_analysis(self, text_id: int) -> bool:
        """Run audio analysis"""
        print("🎵 Running audio analysis...")
        try:
            response = await self.api_client.make_request("POST", f"/api/audio-analysis/{text_id}/analyze")
            if response.status_code in [200, 202]:
                print("✅ Audio analysis completed")
                return True
            else:
                print(f"❌ Audio analysis failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Audio analysis error: {str(e)}")
            return False

    async def run_bg_music_generation(self, text_id: int) -> bool:
        """Run background music generation"""
        print("🎼 Running background music generation...")
        try:
            response = await self.api_client.make_request("POST", f"/api/background-music/{text_id}/process?force=true")
            if response.status_code in [200, 202]:
                print("✅ Background music generation triggered")
                return True
            else:
                print(f"❌ Background music generation failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Background music generation error: {str(e)}")
            return False

    async def run_sfx_generation(self, text_id: int) -> bool:
        """Run sound effects generation"""
        print("🔊 Running sound effects generation...")
        try:
            response = await self.api_client.make_request("POST", f"/api/sound-effects/text/{text_id}/generate?force=true")
            if response.status_code in [200, 202]:
                print("✅ Sound effects generation triggered")
                return True
            else:
                print(f"❌ Sound effects generation failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Sound effects generation error: {str(e)}")
            return False

    async def run_final_audio(self, text_id: int) -> Optional[str]:
        """Run final audio combining"""
        print("🎬 Running final audio export...")
        try:
            response = await self.api_client.make_request("POST", f"/api/export/{text_id}/final-audio")
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

class WebhookTriggeredAudioManager:
    """Manages reactive audio completion triggered by webhooks"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.completion_events = {}  # Track completion events per text_id
    
    async def setup_reactive_completion(self, text_id: int, needs_bg_music: bool, needs_sfx: bool) -> Dict[str, Any]:
        """Setup reactive completion monitoring and trigger final audio when ready"""
        print("🎯 Setting up reactive webhook-triggered audio completion...")
        
        start_time = time.time()
        
        # If nothing to wait for, proceed immediately
        if not needs_bg_music and not needs_sfx:
            print("✅ No audio generation needed, proceeding to final export")
            return {
                "bg_music_completed": True,
                "sfx_completed": True,
                "all_complete": True,
                "completion_time": 0
            }
        
        # Use dedicated webhook waiting functions with parallel execution
        tasks = []
        
        if needs_bg_music:
            print("⏳ Starting background music webhook wait...")
            tasks.append(("bg_music", self._wait_for_background_music(text_id)))
        
        if needs_sfx:
            print("⏳ Starting sound effects webhook wait...")
            tasks.append(("sfx", self._wait_for_sound_effects(text_id)))
        
        # Run webhook waits in parallel
        bg_success = False
        sfx_count = 0
        
        if tasks:
            print(f"🚀 Running {len(tasks)} webhook wait(s) in parallel...")
            results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            
            # Process results
            for i, (task_type, result) in enumerate(zip([task[0] for task in tasks], results)):
                if isinstance(result, Exception):
                    print(f"❌ {task_type} webhook wait failed: {result}")
                elif task_type == "bg_music":
                    bg_success = result
                    if bg_success:
                        print("✅ Background music webhook completed!")
                    else:
                        print("⚠️  Background music webhook timed out")
                elif task_type == "sfx":
                    sfx_count = result
                    if sfx_count > 0:
                        print(f"✅ Sound effects webhooks completed! ({sfx_count} effects)")
                    else:
                        print("⚠️  Sound effects webhooks timed out")
        
        elapsed_time = time.time() - start_time
        
        # Determine completion status
        bg_complete = not needs_bg_music or bg_success
        sfx_complete = not needs_sfx or (sfx_count > 0)
        all_complete = bg_complete and sfx_complete
        
        if all_complete:
            print(f"🎉 All webhooks completed in {elapsed_time:.1f} seconds! Triggering final audio...")
        else:
            print(f"⚠️  Webhook completion status after {elapsed_time:.1f} seconds:")
            print(f"   Background Music: {'✅' if bg_complete else '❌'}")
            print(f"   Sound Effects: {'✅' if sfx_complete else '❌'} ({sfx_count} completed)")
        
        return {
            "bg_music_completed": bg_complete,
            "sfx_completed": sfx_complete,
            "all_complete": all_complete,
            "completion_time": elapsed_time
        }
    
    async def _wait_for_background_music(self, text_id: int) -> bool:
        """Wait for background music webhook using event-driven function"""
        try:
            return await wait_for_webhook_completion_event(
                "background_music", 
                text_id, 
                timeout=self.config.webhook_completion_timeout
            )
        except Exception as e:
            print(f"❌ Error waiting for background music webhook: {e}")
            return False
    
    async def _wait_for_sound_effects(self, text_id: int) -> int:
        """Wait for sound effects webhooks using event-driven function"""
        try:
            return await wait_for_sound_effects_completion_event(
                text_id,
                timeout=self.config.webhook_completion_timeout
            )
        except Exception as e:
            print(f"❌ Error waiting for sound effects webhooks: {e}")
            return 0

class PipelineOrchestrator:
    """Main pipeline orchestrator"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.server_manager = ServerManager(config)
        self.api_client = APIClient(config)
        self.text_manager = TextManager(self.api_client)
        self.data_manager = PipelineDataManager()
        self.steps = PipelineSteps(self.api_client, config)
        self.completion_waiter = WebhookTriggeredAudioManager(config)

    async def run_pipeline(self, text_id: int) -> Dict[str, Any]:
        """Run the complete parallel pipeline"""
        print(f"\n🚀 Starting complete pipeline for text {text_id}")
        print("🎯 Pipeline structure:")
        print("   Track 1: Text Analysis → Voice Generation → Speech Generation")
        print("   Track 2: Audio Analysis → (Background Music || Sound Effects)")
        print("   🔗 Webhook-triggered: Audio generation waits for Replicate webhooks")
        print("   Final: Audio Export (triggered immediately when all webhooks complete)")
        
        results = {}
        start_time = time.time()
        
        # Step 1: Reset all data
        if not await self.data_manager.reset_pipeline_data(text_id):
            results["status"] = "FAILED"
            results["error"] = "Failed to reset pipeline data"
            return results
        
        # Step 2: Run parallel tracks
        async def speech_track():
            """Track 1: Text → Voice → Speech"""
            print("\n🎤 Starting Speech Track...")
            
            # Text analysis
            if not await self.steps.run_text_analysis(text_id):
                return {"speech_track": False, "error": "text_analysis_failed"}
            
            # Voice generation (parallel)
            if not await self.steps.run_voice_generation(text_id):
                return {"speech_track": False, "error": "voice_generation_failed"}
            
            # Speech generation
            if not await self.steps.run_speech_generation(text_id):
                return {"speech_track": False, "error": "speech_generation_failed"}
            
            print("✅ Speech Track completed")
            return {"speech_track": True}
        
        async def audio_track():
            """Track 2: Audio Analysis → (BG Music || SFX)"""
            print("\n🎵 Starting Audio Track...")
            
            # Audio analysis
            if not await self.steps.run_audio_analysis(text_id):
                return {"audio_track": False, "error": "audio_analysis_failed"}
            
            # Parallel audio generation
            print("🚀 Running background music and sound effects in parallel...")
            bg_task = self.steps.run_bg_music_generation(text_id)
            sfx_task = self.steps.run_sfx_generation(text_id)
            
            bg_result, sfx_result = await asyncio.gather(bg_task, sfx_task)
            
            if bg_result or sfx_result:
                print("\n🔗 Pipeline now waiting for Replicate webhooks to deliver audio...")
                print("⏳ Terminal will remain open until all webhooks complete")
                
                # Wait for completion using webhook-triggered approach
                completion_results = await self.completion_waiter.setup_reactive_completion(text_id, bg_result, sfx_result)
                final_bg = completion_results["bg_music_completed"] if bg_result else True
                final_sfx = completion_results["sfx_completed"] if sfx_result else True
                
                if final_bg and final_sfx:
                    print("✅ Audio Track completed")
                    return {"audio_track": True, "webhook_wait_time": completion_results.get("completion_time", 0)}
                else:
                    return {"audio_track": False, "error": "audio_completion_failed", "webhook_wait_time": completion_results.get("completion_time", 0)}
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
        output_path = await self.steps.run_final_audio(text_id)
        
        # Final results
        end_time = time.time()
        results["status"] = "SUCCESS" if output_path else "PARTIAL_SUCCESS"
        results["duration"] = end_time - start_time
        results["webhook_wait_time"] = audio_result.get("webhook_wait_time", 0)
        results["output_path"] = output_path
        
        return results

# Legacy functions for backward compatibility
def check_server_running() -> bool:
    """Check if FastAPI server is running"""
    server_manager = ServerManager(config)
    return server_manager.is_running()

def start_server() -> bool:
    """Start the FastAPI server"""
    global server_process
    server_manager = ServerManager(config)
    result = server_manager.start()
    server_process = server_manager.process
    return result

def ensure_server_running() -> bool:
    """Ensure FastAPI server is running, start if needed"""
    server_manager = ServerManager(config)
    result = server_manager.ensure_running()
    global server_process
    server_process = server_manager.process
    return result

def cleanup_server():
    """Clean up server process on exit"""
    global server_process
    if server_process:
        server_manager = ServerManager(config)
        server_manager.process = server_process
        server_manager.cleanup()
        server_process = None

def get_api_client():
    """Get async HTTP client"""
    api_client = APIClient(config)
    return api_client.get_client()

# Legacy functions for backward compatibility
async def get_or_create_text(text_id: Optional[int] = None) -> Optional[int]:
    """Get text_id from parameter or create from input file"""
    text_manager = TextManager(APIClient(config))
    return await text_manager.get_or_create_text(text_id)

async def reset_pipeline_data(text_id: int) -> bool:
    """Reset all pipeline data for the text"""
    data_manager = PipelineDataManager()
    return await data_manager.reset_pipeline_data(text_id)

# Legacy pipeline service functions
async def run_text_analysis(text_id: int) -> bool:
    """Run text analysis"""
    steps = PipelineSteps(APIClient(config), config)
    return await steps.run_text_analysis(text_id)

async def run_voice_generation(text_id: int) -> bool:
    """Run voice generation in parallel for all characters"""
    steps = PipelineSteps(APIClient(config), config)
    return await steps.run_voice_generation(text_id)

async def run_speech_generation(text_id: int) -> bool:
    """Run speech generation"""
    steps = PipelineSteps(APIClient(config), config)
    return await steps.run_speech_generation(text_id)

async def run_audio_analysis(text_id: int) -> bool:
    """Run audio analysis"""
    steps = PipelineSteps(APIClient(config), config)
    return await steps.run_audio_analysis(text_id)

async def run_bg_music_generation(text_id: int) -> bool:
    """Run background music generation"""
    steps = PipelineSteps(APIClient(config), config)
    return await steps.run_bg_music_generation(text_id)

async def run_sfx_generation(text_id: int) -> bool:
    """Run sound effects generation"""
    steps = PipelineSteps(APIClient(config), config)
    return await steps.run_sfx_generation(text_id)

async def wait_for_audio_completion(text_id: int, bg_music: bool, sfx: bool, max_wait: int = 300) -> Dict[str, Any]:
    """Wait for background music and sound effects to complete"""
    waiter = WebhookTriggeredAudioManager(config)
    return await waiter.setup_reactive_completion(text_id, bg_music, sfx)

async def run_final_audio(text_id: int) -> Optional[str]:
    """Run final audio combining"""
    steps = PipelineSteps(APIClient(config), config)
    return await steps.run_final_audio(text_id)

async def run_pipeline(text_id: int) -> Dict[str, Any]:
    """Run the complete parallel pipeline"""
    orchestrator = PipelineOrchestrator(config)
    return await orchestrator.run_pipeline(text_id)

class PipelineRunner:
    """Main pipeline runner application"""
    
    def __init__(self):
        self.orchestrator = PipelineOrchestrator(config)
        self.server_manager = ServerManager(config)
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.server_manager.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _parse_command_line_args(self) -> Optional[int]:
        """Parse command line arguments"""
        text_id_arg = sys.argv[1] if len(sys.argv) > 1 else None
        if text_id_arg:
            try:
                return int(text_id_arg)
            except ValueError:
                print(f"❌ Invalid text_id: {text_id_arg}")
                return None
        return None
    
    def _display_results(self, results: Dict[str, Any]):
        """Display pipeline results"""
        print(f"\n📊 PIPELINE RESULTS")
        print(f"===================")
        print(f"Status: {results['status']}")
        print(f"Total Duration: {results.get('duration', 0):.2f} seconds")
        
        if results.get("webhook_wait_time"):
            print(f"Webhook Wait Time: {results['webhook_wait_time']:.2f} seconds")
            pipeline_time = results.get('duration', 0) - results.get('webhook_wait_time', 0)
            print(f"Processing Time: {pipeline_time:.2f} seconds")
        
        if results.get("output_path"):
            print(f"Output: {results['output_path']}")
        
        if results.get("error"):
            print(f"Error: {results['error']}")
            return False
        
        print("\n✨ Pipeline completed successfully!")
        print("🔗 Webhooks delivered audio as expected")
        return True
    
    async def run(self) -> bool:
        """Run the complete pipeline"""
        print("🎵 Simple E2E Pipeline")
        print("=====================")
        
        self._setup_signal_handlers()
        
        try:
            # Ensure FastAPI server is running
            if not self.server_manager.ensure_running():
                print("❌ Failed to start FastAPI server")
                return False
            
            # Parse command line arguments
            text_id_input = self._parse_command_line_args()
            
            # Get or create text
            text_manager = TextManager(APIClient(config))
            text_id = await text_manager.get_or_create_text(text_id_input)
            if not text_id:
                print("❌ Failed to get text_id")
                return False
            
            # Run pipeline
            results = await self.orchestrator.run_pipeline(text_id)
            
            # Display results
            return self._display_results(results)
            
        finally:
            # Always cleanup server on exit
            self.server_manager.cleanup()

async def main():
    """Main function"""
    runner = PipelineRunner()
    success = await runner.run()
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 