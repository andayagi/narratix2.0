"""
Shared service for Replicate-based audio generation.

This module provides a DRY (Don't Repeat Yourself) architecture for both sound effects 
and background music generation using Replicate webhooks instead of polling.
"""

import base64
import os
import tempfile
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, Union
from sqlalchemy.orm import Session
import replicate
from utils.config import settings
from utils.logging import get_logger
from utils.http_client import get_sync_client
from db import crud

logger = get_logger(__name__)

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
        # Construct webhook URL with production validation
        webhook_url = settings.get_webhook_url(content_type, content_id)
        
        logger.info(f"Creating {content_type} prediction for ID {content_id} with webhook: {webhook_url}")
        logger.debug(f"Prediction config: {config}")
        
        # Create prediction with webhook
        prediction = replicate.predictions.create(
            version=config.version.split(':')[-1] if ':' in config.version else config.version,
            input=config.input,
            webhook=webhook_url,
            webhook_events_filter=["completed"]
        )
        
        logger.info(f"Created {content_type} prediction {prediction.id} for content ID {content_id}")
        return prediction.id
        
    except Exception as e:
        logger.error(f"Error creating {content_type} prediction for ID {content_id}: {e}")
        raise

def process_webhook_result(content_type: str, content_id: int, prediction_data: Dict[str, Any]) -> bool:
    """
    Process webhook result by downloading audio and routing to appropriate processor.
    
    Args:
        content_type: "sound_effect" or "background_music"
        content_id: effect_id or text_id respectively
        prediction_data: Webhook payload with prediction data
        
    Returns:
        True if processing succeeded, False otherwise
    """
    try:
        # Get processor based on content type
        processor = get_processor(content_type)
        
        # Process the result
        return processor.process_and_store(content_id, prediction_data)
        
    except Exception as e:
        logger.error(f"Error processing {content_type} webhook result for ID {content_id}: {e}")
        return False

def get_processor(content_type: str) -> 'AudioPostProcessor':
    """
    Factory function to get appropriate processor based on content type.
    
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
        raise ValueError(f"Unknown content type: {content_type}")

class AudioPostProcessor(ABC):
    """Abstract base class for audio post-processing."""
    
    def process_and_store(self, content_id: int, prediction_data: Dict[str, Any]) -> bool:
        """
        Main processing pipeline for audio webhook results.
        
        Args:
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
            
            # Download audio from Replicate
            audio_data = self._download_audio(output_url)
            if not audio_data:
                logger.error(f"Failed to download audio for {self.__class__.__name__} ID {content_id}")
                return False
            
            # Trim audio if needed (sound effects only)
            processed_audio = self.trim_audio(audio_data)
            
            # Convert to base64
            audio_b64 = base64.b64encode(processed_audio).decode()
            
            # Store in database
            success = self.store_audio(content_id, audio_b64)
            
            # Log result
            self.log_result(content_id, success, prediction_data)
            
            return success
            
        except Exception as e:
            logger.error(f"Error in {self.__class__.__name__} processing for ID {content_id}: {e}")
            self.log_result(content_id, False, prediction_data, error=str(e))
            return False
    
    def _download_audio(self, url: str) -> Optional[bytes]:
        """Download audio from URL."""
        try:
            client = get_sync_client()
            response = client.get(url, timeout=30)
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
    def store_audio(self, content_id: int, audio_b64: str) -> bool:
        """
        Store audio in database. Override in subclasses.
        
        Args:
            content_id: ID of the content
            audio_b64: Base64 encoded audio
            
        Returns:
            True if storage succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def log_result(self, content_id: int, success: bool, prediction_data: Dict[str, Any], error: Optional[str] = None):
        """
        Log processing result. Override in subclasses.
        
        Args:
            content_id: ID of the content
            success: Whether processing succeeded
            prediction_data: Original prediction data
            error: Error message if any
        """
        pass

class SoundEffectProcessor(AudioPostProcessor):
    """Post-processor for sound effects."""
    
    def trim_audio(self, audio_data: bytes) -> bytes:
        """Trim sound effect audio using ffmpeg."""
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as input_file:
                input_file.write(audio_data)
                input_file.flush()
                
                output_path = input_file.name.replace('.mp3', '_trimmed.mp3')
                
                # Trim using ffmpeg
                cmd = [
                    'ffmpeg', '-i', input_file.name,
                    '-af', 'silenceremove=start_periods=1:start_duration=1:start_threshold=-60dB:detection=peak,aformat=dblp,areverse,silenceremove=start_periods=1:start_duration=1:start_threshold=-60dB:detection=peak,aformat=dblp,areverse',
                    '-y', output_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Read trimmed audio
                    with open(output_path, 'rb') as f:
                        trimmed_data = f.read()
                    
                    # Clean up temp files
                    os.unlink(input_file.name)
                    os.unlink(output_path)
                    
                    return trimmed_data
                else:
                    logger.warning(f"ffmpeg trimming failed: {result.stderr}. Using original audio.")
                    # Clean up temp files
                    os.unlink(input_file.name)
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                    return audio_data
                    
        except Exception as e:
            logger.error(f"Error trimming sound effect audio: {e}")
            return audio_data
    
    def store_audio(self, content_id: int, audio_b64: str) -> bool:
        """Store sound effect audio in database."""
        try:
            from db.database import get_db
            db = next(get_db())
            
            result = crud.update_sound_effect_audio(
                db=db,
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
    
    def log_result(self, content_id: int, success: bool, prediction_data: Dict[str, Any], error: Optional[str] = None):
        """Log sound effect processing result."""
        try:
            from db.database import get_db
            db = next(get_db())
            
            status = "success" if success else "error"
            response_data = {
                "prediction_id": prediction_data.get("id"),
                "output_url": prediction_data.get("output"),
                "success": success
            }
            
            if error:
                response_data["error"] = error
            
            crud.create_log(
                db=db,
                text_id=None,  # Sound effects don't have direct text_id in logs
                operation="sound_effect_generation_webhook",
                status=status,
                response=response_data
            )
            
        except Exception as e:
            logger.error(f"Error logging sound effect result for ID {content_id}: {e}")

class BackgroundMusicProcessor(AudioPostProcessor):
    """Post-processor for background music."""
    
    def trim_audio(self, audio_data: bytes) -> bytes:
        """Background music doesn't need trimming."""
        return audio_data
    
    def store_audio(self, content_id: int, audio_b64: str) -> bool:
        """Store background music audio in database."""
        try:
            from db.database import get_db
            db = next(get_db())
            
            result = crud.update_text_background_music_audio(
                db=db,
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
    
    def log_result(self, content_id: int, success: bool, prediction_data: Dict[str, Any], error: Optional[str] = None):
        """Log background music processing result."""
        try:
            from db.database import get_db
            db = next(get_db())
            
            status = "success" if success else "error"
            response_data = {
                "prediction_id": prediction_data.get("id"),
                "output_url": prediction_data.get("output"),
                "success": success
            }
            
            if error:
                response_data["error"] = error
            
            crud.create_log(
                db=db,
                text_id=content_id,
                operation="background_music_generation_webhook",
                status=status,
                response=response_data
            )
            
        except Exception as e:
            logger.error(f"Error logging background music result for text ID {content_id}: {e}") 