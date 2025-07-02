import json
import os
import subprocess
from typing import Dict, Any, Optional, Tuple
import base64
from sqlalchemy.orm import Session
from utils.config import settings
from utils.logging import get_logger
from utils.http_client import get_sync_client
from db import crud, models
from db.session_manager import managed_db_session
from utils.timing import time_it
from services.clients import ClientFactory

# Initialize logger
logger = get_logger(__name__)

def update_text_with_music_prompt(text_id: int, music_prompt: str) -> bool:
    """
    Update the Text model to include the background music prompt.
    
    Args:
        text_id: ID of the text
        music_prompt: The generated music prompt to store
        
    Returns:
        Boolean indicating success
    """
    try:
        with managed_db_session() as db:
            # Get the text from the database
            db_text = crud.get_text(db, text_id)
            if not db_text:
                logger.error(f"Text with ID {text_id} not found")
                return False
            
            # Update the background music prompt
            db_text.background_music_prompt = music_prompt
            
            # Also log the operation
            crud.create_log(
                db=db,
                text_id=text_id,
                operation="background_music_prompt_generation",
                status="success",
                response={"music_prompt": music_prompt}
            )
        
        return True
    except Exception as e:
        logger.error(f"Error updating text with music prompt: {str(e)}")
        return False 

def get_audio_duration(audio_file_path: str) -> float:
    """
    Get the duration of an audio file in seconds using ffprobe.
    
    Args:
        audio_file_path: Path to the audio file
        
    Returns:
        Duration in seconds, or 0 if error
    """
    try:
        cmd = [
            'ffprobe', 
            '-v', 'error', 
            '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', 
            audio_file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Error getting duration: {result.stderr}")
            return 0
        
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        logger.error(f"Error getting audio duration: {str(e)}")
        return 0

@time_it("background_music_generation")
async def generate_background_music(text_id: int) -> bool:
    """
    Generate background music using Replicate webhook for a text by ID.
    Requires that a background music prompt already exists in the database.
    
    Args:
        text_id: ID of the text to generate background music for
        
    Returns:
        True if webhook was successfully triggered, False otherwise.
    """
    from services.replicate_audio import create_webhook_prediction, ReplicateAudioConfig
    
    try:
        with managed_db_session() as db:
            # Check that background music prompt already exists in the database
            db_text = crud.get_text(db, text_id)
            if not db_text or not db_text.background_music_prompt:
                logger.error(f"Text with ID {text_id} not found or has no background music prompt. Call audio_analysis.py first.")
                return False
            
            music_prompt = db_text.background_music_prompt
            
            # Get segments to calculate required duration
            segments = crud.get_segments_by_text(db, text_id)
            if not segments:
                logger.error(f"No segments found for text with ID {text_id}")
                return False
        
            # Estimate speech duration based on text content (character-based estimation)
            total_chars = sum(len(segment.text or "") for segment in segments)
            
            # Estimate: ~150 words/minute, ~5 chars/word, 60 seconds/minute
            # So: chars_per_second = (150 * 5) / 60 = 12.5
            estimated_speech_duration = total_chars / 12.5
            
            if estimated_speech_duration <= 0:
                logger.error(f"Could not estimate speech duration for text with ID {text_id} (no text content)")
                return False
                
            # Calculate sum of trailing_silence from all segments
            total_trailing_silence = sum(segment.trailing_silence for segment in segments if segment.trailing_silence)
            
            # Music should be at least as long as estimated speech + trailing silence + 10 seconds
            total_duration = estimated_speech_duration + total_trailing_silence + 10
            # Round to the nearest integer - Replicate API doesn't accept fractional durations
            music_duration = int(round(total_duration))
        
            logger.info(f"Generating background music with prompt: {music_prompt}", 
                       extra={"music_prompt": music_prompt, 
                              "total_chars": total_chars,
                              "estimated_speech_duration": estimated_speech_duration,
                              "total_trailing_silence": total_trailing_silence,
                              "calculated_duration": total_duration,
                              "final_music_duration": music_duration})
            
            # Clear existing background music audio data to ensure we wait for new prediction
            if db_text.background_music_audio_b64:
                db_text.background_music_audio_b64 = None
                db.commit()
                logger.info(f"Cleared existing background music audio for text {text_id} to wait for new prediction")
            
            # Create ReplicateAudioConfig with background music parameters
            config = ReplicateAudioConfig(
                version="96af46316252ddea4c6614e31861876183b59dce84bad765f38424e87919dd85",
                input={
                    "prompt": music_prompt,
                    "duration": music_duration,
                    "output_format": "mp3",
                    "temperature": 1,
                    "top_k": 250,
                    "top_p": 0,
                    "classifier_free_guidance": 3
                }
            )
            
            # Trigger webhook prediction
            prediction_id = create_webhook_prediction("background_music", text_id, config)
            
            if not prediction_id:
                logger.error(f"Failed to trigger background music generation webhook for text {text_id}")
                crud.create_log(
                    db=db,
                    text_id=text_id,
                    operation="background_music_generation_webhook_trigger",
                    status="error",
                    response={"error": "Failed to trigger webhook"}
                )
                return False
            
            logger.info(f"Background music generation webhook triggered for text {text_id}, prediction ID: {prediction_id}")
            crud.create_log(
                db=db,
                text_id=text_id,
                operation="background_music_generation_webhook_trigger",
                status="success",
                response={"prediction_id": prediction_id, "message": "Webhook triggered successfully"}
            )
        
        # Import and wait for webhook completion
        from services.replicate_audio import wait_for_webhook_completion_event
        logger.info(f"Waiting for background music generation to complete for text {text_id}...")
        
        success = await wait_for_webhook_completion_event("background_music", text_id)
        
        if success:
            logger.info(f"✅ Background music generation completed successfully for text {text_id}")
            return True
        else:
            logger.error(f"❌ Background music generation failed or timed out for text {text_id}")
            return False

    except Exception as e:
        logger.error(f"Error triggering background music generation webhook: {str(e)}")
        with managed_db_session() as db:
            crud.create_log(db=db, text_id=text_id, operation="background_music_generation_webhook_trigger", status="error", response={"error": str(e)})
        return False

 