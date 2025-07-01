"""
Shared service for Replicate-based audio generation.

This module provides a DRY (Don't Repeat Yourself) architecture for both sound effects 
and background music generation using Replicate webhooks instead of polling.
"""

import asyncio
import base64
import os
import tempfile
import subprocess
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Any, Optional, Union, Generator, List
from sqlalchemy.orm import Session
from utils.config import settings
from utils.logging import get_logger
from utils.http_client import get_sync_client, get_async_client
from utils.ngrok_sync import smart_server_health_check, sync_ngrok_url
from db import crud
from db.session_manager import managed_db_session, managed_db_transaction, DatabaseSessionManager
from services.clients import ClientFactory

logger = get_logger(__name__)

@contextmanager
def managed_temp_files(*suffixes: str) -> Generator[List[str], None, None]:
    """
    Context manager for creating and automatically cleaning up temporary files.
    
    Args:
        *suffixes: File suffixes for temporary files (e.g., '.mp3', '.wav')
        
    Yields:
        List of temporary file paths
        
    Example:
        with managed_temp_files('.mp3', '.mp3') as (input_path, output_path):
            # Use files safely
            pass
        # Files are automatically cleaned up
    """
    temp_files = []
    try:
        for suffix in suffixes:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                temp_files.append(f.name)
        yield temp_files
    finally:
        # Always clean up, even if exceptions occur
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f"Cleaned up temporary file: {file_path}")
            except OSError as e:
                logger.warning(f"Failed to clean up temporary file {file_path}: {e}")

def run_ffmpeg_safely(cmd: List[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """
    Run ffmpeg command with proper error handling and timeout.
    
    Args:
        cmd: ffmpeg command as list of strings
        timeout: Command timeout in seconds (uses config default if None)
        
    Returns:
        CompletedProcess result
        
    Raises:
        subprocess.TimeoutExpired: If command times out
        subprocess.CalledProcessError: If command fails
    """
    if timeout is None:
        timeout = settings.replicate_audio.ffmpeg_timeout
        
    try:
        logger.debug(f"Running ffmpeg command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            check=False  # Don't raise on non-zero exit, we'll handle it
        )
        
        if result.returncode != 0:
            logger.warning(f"ffmpeg command failed with code {result.returncode}: {result.stderr}")
        else:
            logger.debug("ffmpeg command completed successfully")
            
        return result
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"ffmpeg command timed out after {timeout}s: {' '.join(cmd)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error running ffmpeg: {e}")
        raise

class WebhookCompletionNotifier:
    """Event-driven webhook completion notification system for precise E2E timing"""
    
    def __init__(self):
        self.completion_events = {}  # Track completion events per content
        self.completion_times = {}   # Track exact completion times  
        self.lock = asyncio.Lock()
    
    async def create_completion_event(self, content_type: str, content_id: int) -> asyncio.Event:
        """Create an event to wait for webhook completion"""
        async with self.lock:
            key = f"{content_type}_{content_id}"
            event = asyncio.Event()
            self.completion_events[key] = event
            self.completion_times[key] = None
            logger.info(f"Created completion event for {content_type} {content_id}")
            return event
    
    async def notify_completion(self, content_type: str, content_id: int, success: bool):
        """Notify that a webhook has completed"""
        async with self.lock:
            key = f"{content_type}_{content_id}"
            if key in self.completion_events:
                self.completion_times[key] = (time.time(), success)
                self.completion_events[key].set()
                logger.info(f"Notified completion for {content_type} {content_id}: {'success' if success else 'failed'}")
    
    async def wait_for_completion(self, content_type: str, content_id: int, timeout: float) -> tuple[bool, float]:
        """Wait for completion event with timeout"""
        key = f"{content_type}_{content_id}"
        event = self.completion_events.get(key)
        if not event:
            logger.warning(f"No completion event found for {content_type} {content_id}")
            return False, 0
        
        start_time = time.time()
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            completion_time, success = self.completion_times[key]
            elapsed = completion_time - start_time
            logger.info(f"Webhook completion for {content_type} {content_id}: {elapsed:.2f}s")
            return success, elapsed
        except asyncio.TimeoutError:
            logger.warning(f"Webhook completion timeout for {content_type} {content_id} after {timeout}s")
            return False, timeout
    
    def cleanup_event(self, content_type: str, content_id: int):
        """Clean up completion event after use"""
        key = f"{content_type}_{content_id}"
        self.completion_events.pop(key, None)
        self.completion_times.pop(key, None)

class WebhookNotifierFactory:
    """Factory for creating WebhookCompletionNotifier instances."""
    
    @staticmethod
    def create_notifier() -> WebhookCompletionNotifier:
        """Create a new WebhookCompletionNotifier instance."""
        return WebhookCompletionNotifier()
    
    @staticmethod
    def get_global_notifier() -> WebhookCompletionNotifier:
        """Get or create the global notifier instance (for backward compatibility)."""
        if not hasattr(WebhookNotifierFactory, '_global_notifier'):
            WebhookNotifierFactory._global_notifier = WebhookCompletionNotifier()
        return WebhookNotifierFactory._global_notifier

@dataclass
class ReplicateAudioConfig:
    """Configuration for Replicate audio generation."""
    version: str
    input: Dict[str, Any]
    duration: Optional[float] = None

def create_webhook_prediction(content_type: str, content_id: int, config: ReplicateAudioConfig) -> str:
    """
    Create a Replicate prediction with webhook for async processing.
    
    Args:
        content_type: "sound_effect" or "background_music"
        content_id: effect_id or text_id respectively
        config: ReplicateAudioConfig with generation parameters
        
    Returns:
        prediction_id for tracking
    """
    try:
        # For local development, ensure ngrok URL is current before creating webhook
        if not settings.is_production():
            logger.debug("Development environment detected - checking ngrok sync")
            success, current_url = sync_ngrok_url(silent=True)
            if success and current_url:
                logger.debug(f"Ngrok URL synchronized: {current_url}")
            else:
                logger.warning("Failed to sync ngrok URL - webhook may not be reachable")
        
        # Construct webhook URL with production validation
        webhook_url = settings.get_webhook_url(content_type, content_id)
        
        logger.info(f"Creating Replicate prediction with webhook: {webhook_url}")
        
        # Create prediction with webhook
        client = ClientFactory.get_replicate_client()
        prediction = client.predictions.create(
            version=config.version,
            input=config.input,
            webhook=webhook_url,
            webhook_events_filter=["completed"]
        )
        
        prediction_id = prediction.id
        logger.info(f"Created Replicate prediction {prediction_id} for {content_type} {content_id}")
        
        return prediction_id
        
    except Exception as e:
        logger.error(f"Error creating Replicate prediction for {content_type} {content_id}: {e}")
        return None

async def process_webhook_result(content_type: str, content_id: int, prediction_data: Dict[str, Any], 
                               notifier: Optional[WebhookCompletionNotifier] = None) -> bool:
    """
    Process webhook result using appropriate processor with dependency injection.
    
    Args:
        content_type: "sound_effect" or "background_music"
        content_id: effect_id or text_id respectively
        prediction_data: Webhook payload with prediction data
        notifier: Optional webhook notifier instance (uses global if None)
        
    Returns:
        True if processing succeeded, False otherwise
    """
    if notifier is None:
        notifier = WebhookNotifierFactory.get_global_notifier()
        
    try:
        # Use managed session for processing
        with managed_db_session() as db:
            processor = get_processor(content_type)
            success = await processor.process_and_store(db, content_id, prediction_data)
            
            # Notify completion for event-driven waiting (now properly awaited)
            await notifier.notify_completion(content_type, content_id, success)
            
            return success
            
    except Exception as e:
        logger.error(f"Error processing webhook result for {content_type} {content_id}: {e}")
        await notifier.notify_completion(content_type, content_id, False)
        return False

def get_processor(content_type: str) -> 'AudioPostProcessor':
    """
    Factory function to get the appropriate processor based on content type.
    
    Args:
        content_type: "sound_effect" or "background_music"
        
    Returns:
        AudioPostProcessor instance
    """
    if content_type == "sound_effect":
        return SoundEffectProcessor()
    elif content_type == "background_music":
        return BackgroundMusicProcessor()
    else:
        raise ValueError(f"Unknown content_type: {content_type}")

class AudioPostProcessor(ABC):
    """Abstract base class for audio post-processing with dependency injection support."""
    
    async def process_and_store(self, db: Session, content_id: int, prediction_data: Dict[str, Any]) -> bool:
        """
        Main processing pipeline for audio webhook results with injected database session.
        
        Args:
            db: Database session (injected dependency)
            content_id: ID of the content (effect_id or text_id)
            prediction_data: Webhook payload with prediction data
            
        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Extract output URL from prediction
            output_url = prediction_data.get("output")
            if not output_url:
                logger.error(f"No output URL in prediction data for {self.__class__.__name__} ID {content_id}")
                return False
            
            # Download audio from Replicate (now async)
            audio_data = await self._download_audio(output_url)
            if not audio_data:
                logger.error(f"Failed to download audio for {self.__class__.__name__} ID {content_id}")
                return False
            
            # Trim audio if needed (sound effects only)
            processed_audio = self.trim_audio(audio_data)
            
            # Convert to base64
            audio_b64 = base64.b64encode(processed_audio).decode()
            
            # Store in database using injected session and transaction management
            with managed_db_transaction(db) as tx_db:
                success = await self.store_audio(tx_db, content_id, audio_b64)
                
                # Log result in the same transaction
                await self.log_result(tx_db, content_id, success, prediction_data)
            
            logger.info(f"Successfully processed audio for {self.__class__.__name__} ID {content_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error in {self.__class__.__name__} processing for ID {content_id}: {e}")
            # Log error in separate transaction to ensure it's recorded
            try:
                with managed_db_transaction(db) as tx_db:
                    await self.log_result(tx_db, content_id, False, prediction_data, error=str(e))
            except Exception as log_error:
                logger.error(f"Failed to log error result: {log_error}")
            return False
    
    async def _download_audio(self, url: str) -> Optional[bytes]:
        """Download audio from URL asynchronously."""
        try:
            client = get_async_client()
            response = await client.get(url, timeout=settings.replicate_audio.download_timeout)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error downloading audio from {url}: {e}")
            return None
    
    @abstractmethod
    def trim_audio(self, audio_data: bytes) -> bytes:
        """
        Trim audio if needed. Override in subclasses.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Processed audio bytes
        """
        pass
    
    @abstractmethod
    async def store_audio(self, db: Session, content_id: int, audio_b64: str) -> bool:
        """
        Store audio in database. Override in subclasses.
        
        Args:
            db: Database session (injected dependency)
            content_id: ID of the content
            audio_b64: Base64 encoded audio
            
        Returns:
            True if storage succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    async def log_result(self, db: Session, content_id: int, success: bool, prediction_data: Dict[str, Any], error: Optional[str] = None):
        """
        Log processing result. Override in subclasses.
        
        Args:
            db: Database session (injected dependency)
            content_id: ID of the content
            success: Whether processing succeeded
            prediction_data: Original prediction data
            error: Error message if any
        """
        pass

class SoundEffectProcessor(AudioPostProcessor):
    """Post-processor for sound effects with dependency injection."""
    
    def trim_audio(self, audio_data: bytes) -> bytes:
        """Trim sound effect audio using ffmpeg."""
        try:
            with managed_temp_files('.mp3', '.mp3') as (input_path, output_path):
                # Write audio data to input file
                with open(input_path, 'wb') as f:
                    f.write(audio_data)
                
                # Run ffmpeg command with configurable silence threshold
                silence_filter = f'silenceremove=start_periods=1:start_duration=1:start_threshold={settings.replicate_audio.silence_threshold}:detection=peak,aformat=dblp,areverse,silenceremove=start_periods=1:start_duration=1:start_threshold={settings.replicate_audio.silence_threshold}:detection=peak,aformat=dblp,areverse'
                cmd = [
                    'ffmpeg', '-i', input_path,
                    '-af', silence_filter,
                    '-y', output_path
                ]
                
                result = run_ffmpeg_safely(cmd)
                
                if result.returncode == 0:
                    # Read trimmed audio
                    with open(output_path, 'rb') as f:
                        trimmed_data = f.read()
                    
                    return trimmed_data
                else:
                    logger.warning(f"ffmpeg trimming failed: {result.stderr}. Using original audio.")
                    return audio_data
                    
        except Exception as e:
            logger.error(f"Error trimming sound effect audio: {e}")
            return audio_data
    
    async def store_audio(self, db: Session, content_id: int, audio_b64: str) -> bool:
        """Store sound effect audio in database using injected session."""
        try:
            result = DatabaseSessionManager.safe_execute(
                db, 
                f"update_sound_effect_audio_{content_id}",
                crud.update_sound_effect_audio,
                effect_id=content_id,
                audio_data_b64=audio_b64
            )
            
            if result:
                logger.info(f"Successfully stored audio for sound effect {content_id}")
                return True
            else:
                logger.error(f"Failed to update sound effect {content_id} in database")
                return False
                
        except Exception as e:
            logger.error(f"Error storing sound effect audio for ID {content_id}: {e}")
            return False
    
    async def log_result(self, db: Session, content_id: int, success: bool, prediction_data: Dict[str, Any], error: Optional[str] = None):
        """Log sound effect processing result using injected session."""
        try:
            status = "success" if success else "error"
            response_data = {
                "prediction_id": prediction_data.get("id"),
                "output_url": prediction_data.get("output"),
                "success": success
            }
            
            if error:
                response_data["error"] = error
            
            DatabaseSessionManager.safe_execute(
                db,
                f"log_sound_effect_result_{content_id}",
                crud.create_log,
                text_id=None,  # Sound effects don't have direct text_id in logs
                operation="sound_effect_generation_webhook",
                status=status,
                response=response_data
            )
            
        except Exception as e:
            logger.error(f"Error logging sound effect result for ID {content_id}: {e}")

class BackgroundMusicProcessor(AudioPostProcessor):
    """Post-processor for background music with dependency injection."""
    
    def trim_audio(self, audio_data: bytes) -> bytes:
        """Background music doesn't need trimming."""
        return audio_data
    
    async def store_audio(self, db: Session, content_id: int, audio_b64: str) -> bool:
        """Store background music audio in database using injected session."""
        try:
            result = DatabaseSessionManager.safe_execute(
                db,
                f"update_background_music_audio_{content_id}",
                crud.update_text_background_music_audio,
                text_id=content_id,
                audio_data_b64=audio_b64
            )
            
            if result:
                logger.info(f"Successfully stored background music audio for text {content_id}")
                return True
            else:
                logger.error(f"Failed to update background music for text {content_id} in database")
                return False
                
        except Exception as e:
            logger.error(f"Error storing background music audio for text ID {content_id}: {e}")
            return False
    
    async def log_result(self, db: Session, content_id: int, success: bool, prediction_data: Dict[str, Any], error: Optional[str] = None):
        """Log background music processing result using injected session."""
        try:
            status = "success" if success else "error"
            response_data = {
                "prediction_id": prediction_data.get("id"),
                "output_url": prediction_data.get("output"),
                "success": success
            }
            
            if error:
                response_data["error"] = error
            
            DatabaseSessionManager.safe_execute(
                db,
                f"log_background_music_result_{content_id}",
                crud.create_log,
                text_id=content_id,
                operation="background_music_generation_webhook",
                status=status,
                response=response_data
            )
            
        except Exception as e:
            logger.error(f"Error logging background music result for text ID {content_id}: {e}")

async def wait_for_webhook_completion_event(content_type: str, content_id: int, timeout: Optional[int] = None,
                                          notifier: Optional[WebhookCompletionNotifier] = None) -> bool:
    """
    Wait for webhook completion using event-driven approach with precise timing.
    
    Args:
        content_type: "sound_effect" or "background_music"
        content_id: ID of the content to wait for
        timeout: Maximum time to wait in seconds (uses config default if None)
        notifier: Optional webhook notifier instance (uses global if None)
        
    Returns:
        True if webhook completed successfully within timeout, False otherwise
    """
    if timeout is None:
        timeout = settings.replicate_audio.webhook_timeout
        
    if notifier is None:
        notifier = WebhookNotifierFactory.get_global_notifier()
        
    try:
        # Create completion event
        event = await notifier.create_completion_event(content_type, content_id)
        
        # Wait for completion
        success, elapsed_time = await notifier.wait_for_completion(content_type, content_id, timeout)
        
        # Clean up the event
        notifier.cleanup_event(content_type, content_id)
        
        logger.info(f"Webhook completion for {content_type} {content_id}: {'success' if success else 'failed'} in {elapsed_time:.2f}s")
        return success
        
    except Exception as e:
        logger.error(f"Error waiting for webhook completion: {e}")
        return False

async def wait_for_sound_effects_completion_event(text_id: int, timeout: Optional[int] = None,
                                                 notifier: Optional[WebhookCompletionNotifier] = None) -> int:
    """
    Wait for all sound effects of a text to complete using event-driven approach.
    
    Args:
        text_id: ID of the text whose sound effects to wait for
        timeout: Maximum time to wait in seconds (uses config default if None)
        notifier: Optional webhook notifier instance (uses global if None)
        
    Returns:
        Number of sound effects that completed successfully
    """
    if timeout is None:
        timeout = settings.replicate_audio.sound_effects_timeout
        
    if notifier is None:
        notifier = WebhookNotifierFactory.get_global_notifier()
        
    try:
        with managed_db_session() as db:
            # Get all sound effects for this text
            effects = crud.get_sound_effects_by_text(db, text_id)
            
            if not effects:
                logger.info(f"No sound effects found for text {text_id}")
                return 0
            
            logger.info(f"Waiting for {len(effects)} sound effects to complete for text {text_id}")
            
            # Create events for all effects
            tasks = []
            for effect in effects:
                task = wait_for_webhook_completion_event("sound_effect", effect.id, timeout, notifier)
                tasks.append(task)
            
            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful completions
            success_count = sum(1 for result in results if result is True)
            
            logger.info(f"Sound effects completion for text {text_id}: {success_count}/{len(effects)} successful")
            return success_count
            
    except Exception as e:
        logger.error(f"Error waiting for sound effects completion: {e}")
        return 0