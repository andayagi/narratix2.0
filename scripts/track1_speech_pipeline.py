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
Track 1 Speech Pipeline - Text Analysis → Voice Generation → Speech Generation
Focused on timing measurement without webhook dependencies.

Usage:
    python3 scripts/track1_speech_pipeline.py [text_id]
    
If no text_id provided, uses input_interactive_e2e.txt
"""

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.database import SessionLocal
from db import crud

# Configuration
@dataclass
class PipelineConfig:
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    long_timeout: float = 6000.0
    server_startup_timeout: int = 30
    server_startup_check_interval: int = 1
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
                if self.is_running():
                    print(f"✅ FastAPI server started")
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
        if self.is_running():
            print(f"✅ FastAPI server already running")
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
                    "title": "Track 1 Speech Pipeline"
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
    
    async def reset_speech_data(self, text_id: int) -> bool:
        """Reset speech-related pipeline data for the text"""
        print(f"🗑️  Resetting speech pipeline data for text {text_id}...")
        
        try:
            db = SessionLocal()
            try:
                text_obj = crud.get_text(db, text_id)
                if not text_obj:
                    print(f"❌ Text {text_id} not found")
                    return False
                
                # Clear text analysis data only
                text_obj.analyzed = False
                text_obj.word_timestamps = None
                
                # Delete characters and segments only (keep sound effects for track 2)
                deleted_characters = crud.delete_characters_by_text(db, text_id)
                deleted_segments = crud.delete_segments_by_text(db, text_id)
                
                db.commit()
                
                print(f"✅ Reset complete: {deleted_characters} characters, {deleted_segments} segments")
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Error resetting speech pipeline data: {str(e)}")
            return False

class SpeechPipelineSteps:
    """Speech pipeline step implementations"""
    
    def __init__(self, api_client: APIClient, config: PipelineConfig):
        self.api_client = api_client
        self.config = config

    async def run_text_analysis(self, text_id: int) -> bool:
        """Run text analysis and wait for completion."""
        print("📝 Running text analysis...")
        step_start = time.time()
        
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
                        elapsed = time.time() - step_start
                        print(f"✅ Text analysis completed in {elapsed:.2f}s")
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
        step_start = time.time()
        
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
                elapsed = time.time() - step_start
                print(f"✅ All characters already have voices ({elapsed:.2f}s)")
                return True
            
            print(f"🚀 Generating voices for {len(characters_needing_voices)} characters in parallel...")
            
            async def generate_voice(character):
                char_start = time.time()
                response = await self.api_client.make_request(
                    "POST", f"/api/character/{character['id']}/voice",
                    json={"text_id": text_id}
                )
                success = response.status_code == 200
                char_elapsed = time.time() - char_start
                print(f"{'✅' if success else '❌'} Voice for {character['name']}: {'Success' if success else 'Failed'} ({char_elapsed:.2f}s)")
                return success
            
            # Execute all voice generations in parallel
            results = await asyncio.gather(*[generate_voice(char) for char in characters_needing_voices])
            success_count = sum(results)
            
            elapsed = time.time() - step_start
            print(f"✅ Voice generation: {success_count}/{len(characters_needing_voices)} successful ({elapsed:.2f}s)")
            return success_count == len(characters_needing_voices)
            
        except Exception as e:
            print(f"❌ Voice generation error: {str(e)}")
            return False

    async def run_speech_generation(self, text_id: int) -> bool:
        """Run speech generation"""
        print("🗣️  Running speech generation...")
        step_start = time.time()
        
        try:
            response = await self.api_client.make_request("POST", f"/api/audio/text/{text_id}/generate-segments")
            if response.status_code == 200:
                elapsed = time.time() - step_start
                print(f"✅ Speech generation completed in {elapsed:.2f}s")
                await asyncio.sleep(self.config.post_speech_generation_wait)  # Wait for files to be saved
                return True
            else:
                print(f"❌ Speech generation failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Speech generation error: {str(e)}")
            return False

class SpeechPipelineOrchestrator:
    """Speech pipeline orchestrator"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.server_manager = ServerManager(config)
        self.api_client = APIClient(config)
        self.text_manager = TextManager(self.api_client)
        self.data_manager = PipelineDataManager()
        self.steps = SpeechPipelineSteps(self.api_client, config)

    async def run_speech_pipeline(self, text_id: int) -> Dict[str, Any]:
        """Run the speech pipeline track"""
        print(f"\n🚀 Starting Speech Pipeline for text {text_id}")
        print("🎯 Pipeline: Text Analysis → Voice Generation → Speech Generation")
        
        results = {}
        pipeline_start = time.time()
        
        # Step 1: Reset speech data
        if not await self.data_manager.reset_speech_data(text_id):
            results["status"] = "FAILED"
            results["error"] = "Failed to reset speech pipeline data"
            return results
        
        # Step 2: Text analysis
        text_start = time.time()
        if not await self.steps.run_text_analysis(text_id):
            results["status"] = "FAILED"
            results["error"] = "text_analysis_failed"
            return results
        results["text_analysis_time"] = time.time() - text_start
        
        # Step 3: Voice generation
        voice_start = time.time()
        if not await self.steps.run_voice_generation(text_id):
            results["status"] = "FAILED"
            results["error"] = "voice_generation_failed"
            return results
        results["voice_generation_time"] = time.time() - voice_start
        
        # Step 4: Speech generation
        speech_start = time.time()
        if not await self.steps.run_speech_generation(text_id):
            results["status"] = "FAILED" 
            results["error"] = "speech_generation_failed"
            return results
        results["speech_generation_time"] = time.time() - speech_start
        
        # Final results
        results["status"] = "SUCCESS"
        results["total_duration"] = time.time() - pipeline_start
        
        return results

class SpeechPipelineRunner:
    """Main speech pipeline runner application"""
    
    def __init__(self):
        self.orchestrator = SpeechPipelineOrchestrator(config)
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
        print(f"\n📊 SPEECH PIPELINE RESULTS")
        print(f"==========================")
        print(f"Status: {results['status']}")
        print(f"Total Duration: {results.get('total_duration', 0):.2f} seconds")
        
        if results.get("text_analysis_time"):
            print(f"📝 Text Analysis: {results['text_analysis_time']:.2f}s")
        if results.get("voice_generation_time"):
            print(f"🎙️  Voice Generation: {results['voice_generation_time']:.2f}s")
        if results.get("speech_generation_time"):
            print(f"🗣️  Speech Generation: {results['speech_generation_time']:.2f}s")
        
        if results.get("error"):
            print(f"Error: {results['error']}")
            return False
        
        print("\n✨ Speech pipeline completed successfully!")
        return True
    
    async def run(self) -> bool:
        """Run the speech pipeline"""
        print("🎤 Track 1 Speech Pipeline")
        print("=========================")
        
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
            
            # Run speech pipeline
            results = await self.orchestrator.run_speech_pipeline(text_id)
            
            # Display results
            return self._display_results(results)
            
        finally:
            # Always cleanup server on exit
            self.server_manager.cleanup()

async def main():
    """Main function"""
    runner = SpeechPipelineRunner()
    success = await runner.run()
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 