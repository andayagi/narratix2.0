#!/usr/bin/env python3
import asyncio
import os
import sys
import time
import subprocess
import requests
import signal
import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager
import logging

"""
Track 2 Audio Pipeline - Audio Analysis → Background Music || Sound Effects
Focused on timing measurement with webhook completion tracking.

Usage:
    python3 scripts/track2_audio_pipeline.py [text_id]
    
Requires existing text_id with completed speech generation.
"""

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.replicate_audio import (
    wait_for_webhook_completion_event, wait_for_sound_effects_completion_event
)
from utils.ngrok_sync import smart_server_health_check, sync_ngrok_url
from utils.config import settings

# Configuration
@dataclass
class PipelineConfig:
    """Simplified configuration for Track 2 audio pipeline"""
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    long_timeout: float = 6000.0
    server_startup_timeout: int = 30
    webhook_timeout: int = 600
    
    @property
    def base_url(self) -> str:
        return os.getenv("BASE_URL", f"http://{self.server_host}:{self.server_port}")

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
        return smart_server_health_check()
    
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
                if self.is_running():
                    print(f"✅ FastAPI server started and ready")
                    return True
                time.sleep(1)  # Fixed interval
                print(f"⏳ Waiting for server to start... ({i+1}/{self.config.server_startup_timeout})")
            
            print(f"❌ Server failed to start within {self.config.server_startup_timeout} seconds")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start server: {str(e)}")
            return False
    
    def ensure_running(self) -> bool:
        """Ensure FastAPI server is running, start if needed"""
        if self.is_running():
            print("✅ FastAPI server already running")
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

class AudioPipelineSteps:
    """Audio pipeline step implementations"""
    
    def __init__(self, api_client: APIClient, config: PipelineConfig):
        self.api_client = api_client
        self.config = config

    async def run_audio_analysis(self, text_id: int) -> bool:
        """Run audio analysis"""
        print("🎵 Running audio analysis...")
        step_start = time.time()
        
        try:
            response = await self.api_client.make_request("POST", f"/api/audio-analysis/{text_id}/analyze")
            if response.status_code in [200, 202]:
                elapsed = time.time() - step_start
                print(f"✅ Audio analysis completed in {elapsed:.2f}s")
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
        step_start = time.time()
        
        try:
            response = await self.api_client.make_request("POST", f"/api/background-music/{text_id}/process?force=true")
            if response.status_code in [200, 202]:
                elapsed = time.time() - step_start
                print(f"✅ Background music generation triggered in {elapsed:.2f}s")
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
        step_start = time.time()
        
        try:
            response = await self.api_client.make_request("POST", f"/api/sound-effects/text/{text_id}/generate?force=true")
            if response.status_code in [200, 202]:
                elapsed = time.time() - step_start
                print(f"✅ Sound effects generation triggered in {elapsed:.2f}s")
                return True
            else:
                print(f"❌ Sound effects generation failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Sound effects generation error: {str(e)}")
            return False

async def wait_for_audio_completion(text_id: int, bg_triggered: bool, sfx_triggered: bool, timeout: int = 600) -> Dict[str, Any]:
    """Event-driven webhook completion for precise E2E timing"""
    print("🎯 Waiting for webhook completion events (real-time notifications)...")
    
    start_time = time.time()
    
    # If nothing was triggered, proceed immediately
    if not bg_triggered and not sfx_triggered:
        print("✅ No webhook audio generation was triggered")
        return {
            "bg_music_completed": False,
            "sfx_completed": False, 
            "all_complete": True,
            "completion_time": 0
        }
    
    # Use event-driven completion waiting for precise timing
    tasks = []
    
    if bg_triggered:
        print("🔗 Setting up background music completion event...")
        tasks.append(("bg_music", wait_for_webhook_completion_event("background_music", text_id, timeout)))
    
    if sfx_triggered:
        print("🔗 Setting up sound effects completion events...")
        tasks.append(("sfx", wait_for_sound_effects_completion_event(text_id, timeout)))
    
    # Execute in parallel and get precise timing
    bg_success = False
    sfx_count = 0
    
    if tasks:
        print(f"⚡ Waiting for {len(tasks)} real-time webhook notification(s)...")
        results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
        
        for (task_type, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                print(f"❌ {task_type} webhook error: {result}")
            elif task_type == "bg_music":
                bg_success = result
                print(f"{'✅' if bg_success else '⏰'} Background music: {'completed' if bg_success else 'timeout'}")
            elif task_type == "sfx":
                sfx_count = result
                print(f"{'✅' if sfx_count > 0 else '⏰'} Sound effects: {sfx_count} completed")
    
    elapsed_time = time.time() - start_time
    bg_complete = not bg_triggered or bg_success
    sfx_complete = not sfx_triggered or (sfx_count > 0)
    all_complete = bg_complete and sfx_complete
    
    return {
        "bg_music_completed": bg_success if bg_triggered else False,
        "sfx_completed": (sfx_count > 0) if sfx_triggered else False,
        "all_complete": all_complete,
        "completion_time": elapsed_time
    }

class AudioPipelineOrchestrator:
    """Audio pipeline orchestrator"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.server_manager = ServerManager(config)
        self.api_client = APIClient(config)
        self.steps = AudioPipelineSteps(self.api_client, config)

    async def run_audio_pipeline(self, text_id: int) -> Dict[str, Any]:
        """Run the audio pipeline track"""
        print(f"\n🚀 Starting Audio Pipeline for text {text_id}")
        print("🎯 Pipeline: Audio Analysis → (Background Music || Sound Effects) → Webhook Wait")
        
        results = {}
        pipeline_start = time.time()
        
        # Step 1: Audio analysis
        audio_analysis_start = time.time()
        if not await self.steps.run_audio_analysis(text_id):
            results["status"] = "FAILED"
            results["error"] = "audio_analysis_failed"
            return results
        results["audio_analysis_time"] = time.time() - audio_analysis_start
        
        # Step 2: Parallel audio generation
        print("🚀 Running background music and sound effects in parallel...")
        parallel_start = time.time()
        
        bg_task = self.steps.run_bg_music_generation(text_id)
        sfx_task = self.steps.run_sfx_generation(text_id)
        
        bg_triggered, sfx_triggered = await asyncio.gather(bg_task, sfx_task)
        results["audio_generation_time"] = time.time() - parallel_start
        
        # If neither audio generation was triggered successfully, fail
        if not (bg_triggered or sfx_triggered):
            results["status"] = "FAILED"
            results["error"] = "no_audio_generation_triggered"
            results["bg_music_triggered"] = False
            results["sfx_triggered"] = False
            results["bg_music_completed"] = False
            results["sfx_completed"] = False
            results["total_duration"] = time.time() - pipeline_start
            return results
        
        # Step 3: Wait for webhook completion for only the triggered audio
        print("\n🔗 Pipeline now waiting for Replicate webhooks to deliver audio...")
        webhook_start = time.time()
        
        completion_results = await wait_for_audio_completion(
            text_id, bg_triggered, sfx_triggered, self.config.webhook_timeout
        )
        results["webhook_wait_time"] = completion_results["completion_time"]
        
        # Final status determination: pipeline succeeds if webhooks completed for what was triggered
        bg_final = completion_results["bg_music_completed"] if bg_triggered else True  # True if not needed
        sfx_final = completion_results["sfx_completed"] if sfx_triggered else True     # True if not needed
        
        if bg_final and sfx_final:
            results["status"] = "SUCCESS"
        else:
            results["status"] = "PARTIAL_SUCCESS"
            if bg_triggered and not completion_results["bg_music_completed"]:
                results["error"] = "background_music_webhook_failed"
            elif sfx_triggered and not completion_results["sfx_completed"]:
                results["error"] = "sound_effects_webhook_failed"
            else:
                results["error"] = "webhook_completion_failed"
        
        # Final results
        results["total_duration"] = time.time() - pipeline_start
        results["bg_music_triggered"] = bg_triggered
        results["sfx_triggered"] = sfx_triggered
        results["bg_music_completed"] = completion_results["bg_music_completed"]
        results["sfx_completed"] = completion_results["sfx_completed"]
        
        return results

class AudioPipelineRunner:
    """Main audio pipeline runner application"""
    
    def __init__(self):
        self.orchestrator = AudioPipelineOrchestrator(config)
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
        print("❌ text_id is required for Track 2 Audio Pipeline")
        print("Usage: python3 scripts/track2_audio_pipeline.py <text_id>")
        return None
    
    def _display_results(self, results: Dict[str, Any]):
        """Display pipeline results"""
        print(f"\n📊 AUDIO PIPELINE RESULTS")
        print(f"=========================")
        print(f"Status: {results['status']}")
        print(f"Total Duration: {results.get('total_duration', 0):.2f} seconds")
        
        if results.get("audio_analysis_time"):
            print(f"🎵 Audio Analysis: {results['audio_analysis_time']:.2f}s")
        if results.get("audio_generation_time"):
            print(f"🚀 Audio Generation (parallel): {results['audio_generation_time']:.2f}s")
        if results.get("webhook_wait_time"):
            print(f"🔗 Webhook Wait: {results['webhook_wait_time']:.2f}s")
        
        # Processing vs waiting breakdown
        if results.get("webhook_wait_time"):
            processing_time = results.get('total_duration', 0) - results.get('webhook_wait_time', 0)
            print(f"📊 Processing Time: {processing_time:.2f}s")
            wait_percentage = (results.get('webhook_wait_time', 0) / results.get('total_duration', 1)) * 100
            print(f"📊 Wait Time: {wait_percentage:.1f}% of total")
        
        # Detailed status for each audio type
        bg_triggered = results.get('bg_music_triggered', False)
        bg_completed = results.get('bg_music_completed', False)
        sfx_triggered = results.get('sfx_triggered', False)
        sfx_completed = results.get('sfx_completed', False)
        
        # Background Music Status
        if bg_triggered:
            bg_status = "✅ Triggered → " + ("✅ Completed" if bg_completed else "❌ Webhook Failed")
        else:
            bg_status = "❌ API Failed → ❌ Not Completed"
        print(f"🎼 Background Music: {bg_status}")
        
        # Sound Effects Status
        if sfx_triggered:
            sfx_status = "✅ Triggered → " + ("✅ Completed" if sfx_completed else "❌ Webhook Failed")
        else:
            sfx_status = "❌ API Failed → ❌ Not Completed"
        print(f"🔊 Sound Effects: {sfx_status}")
        
        # Error details
        if results.get("error"):
            error_msg = results['error']
            if error_msg == "no_audio_generation_triggered":
                print(f"❌ Error: Both background music and sound effects API calls failed")
            elif error_msg == "background_music_webhook_failed":
                print(f"❌ Error: Background music was triggered but webhook failed")
            elif error_msg == "sound_effects_webhook_failed":
                print(f"❌ Error: Sound effects were triggered but webhook failed")
            else:
                print(f"❌ Error: {error_msg}")
        
        # Overall success determination
        if results['status'] == 'SUCCESS':
            if bg_triggered or sfx_triggered:
                print("\n✨ Audio pipeline completed successfully!")
                return True
            else:
                print("\n⚠️  Audio pipeline completed but no audio was generated")
                return False
        elif results['status'] == 'PARTIAL_SUCCESS':
            print("\n⚠️  Audio pipeline completed with some failures")
            return False
        else:
            print("\n❌ Audio pipeline failed")
            return False
    
    async def run(self) -> bool:
        """Run the audio pipeline"""
        print("🎵 Track 2 Audio Pipeline")
        print("=========================")
        
        self._setup_signal_handlers()
        
        # Sync ngrok URL at startup
        print("🔗 Syncing ngrok URL...")
        success, ngrok_url = sync_ngrok_url()
        if success and ngrok_url:
            print(f"✅ Using ngrok URL: {ngrok_url}")
        else:
            print("⚠️  Could not sync ngrok URL, using localhost")
        
        try:
            # Step 1: Check server health and webhook accessibility (like background_music_standalone.py)
            print("🔗 Checking server health and webhook accessibility...")
            
            if not smart_server_health_check():
                print("❌ Server is not accessible - cannot receive webhooks")
                print("📋 Required setup:")
                print("   1. Start FastAPI server: uvicorn api.main:app --host 127.0.0.1 --port 8000")
                print("   2. Start ngrok tunnel: ngrok http 8000") 
                print("   3. Ensure BASE_URL environment variable is set to ngrok URL")
                return False
            
            print("✅ Server is accessible and ready for webhooks")
            
            # Parse command line arguments
            text_id = self._parse_command_line_args()
            if not text_id:
                return False
            
            # Run audio pipeline
            results = await self.orchestrator.run_audio_pipeline(text_id)
            
            # Display results
            return self._display_results(results)
            
        finally:
            # Always cleanup server on exit
            self.server_manager.cleanup()

async def main():
    """Main function"""
    runner = AudioPipelineRunner()
    success = await runner.run()
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 