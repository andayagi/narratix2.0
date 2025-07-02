#!/usr/bin/env python3
"""
Pipeline Orchestration Service

Contains shared infrastructure and orchestration logic for running
text-to-audio pipelines with timing measurement and webhook management.
"""

import asyncio
import os
import sys
import time
import subprocess
import signal
import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager
import logging

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.database import SessionLocal
from db import crud
from utils.ngrok_sync import smart_server_health_check, sync_ngrok_url
from services.replicate_audio import wait_for_webhook_completion_event, wait_for_sound_effects_completion_event

# Configuration
@dataclass
class PipelineConfig:
    """Configuration for pipeline orchestration"""
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    long_timeout: float = 6000.0
    server_startup_timeout: int = 30
    webhook_timeout: int = 600
    post_speech_generation_wait: int = 3
    
    @property
    def base_url(self) -> str:
        return os.getenv("BASE_URL", f"http://{self.server_host}:{self.server_port}")

# Setup logging
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
                time.sleep(1)
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
                    "title": "Pipeline Processing"
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
                deleted_segments = crud.delete_segments_by_text(db, text_id)
                deleted_characters = crud.delete_characters_by_text(db, text_id)
                
                db.commit()
                
                print(f"✅ Reset complete: {deleted_characters} characters, {deleted_segments} segments")
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Error resetting speech pipeline data: {str(e)}")
            return False
    
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
                
                # Delete all related data (in dependency order)
                deleted_sound_effects = crud.delete_sound_effects_by_text(db, text_id)
                deleted_segments = crud.delete_segments_by_text(db, text_id)
                deleted_characters = crud.delete_characters_by_text(db, text_id)
                
                db.commit()
                
                print(f"✅ Reset complete: {deleted_characters} characters, {deleted_segments} segments, {deleted_sound_effects} sound effects")
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Error resetting pipeline data: {str(e)}")
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