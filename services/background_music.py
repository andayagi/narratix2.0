import replicate
from anthropic import Anthropic
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
from utils.timing import time_it

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# Initialize logger
logger = get_logger(__name__)

@time_it("background_music_prompt_generation")
def generate_background_music_prompt(db: Session, text_id: int) -> Optional[str]:
    """
    Generate a background music prompt using unified audio analysis.
    
    Args:
        db: Database session
        text_id: ID of the text to generate background music for
        
    Returns:
        The generated background music prompt, or None if error
    """
    from services.audio_analysis import analyze_text_for_audio
    
    try:
        # Use unified analysis to get soundscape
        soundscape, _ = analyze_text_for_audio(db, text_id)
        
        if soundscape:
            # Store the prompt in the database
            update_text_with_music_prompt(db, text_id, soundscape)
            return soundscape
        else:
            logger.error(f"No soundscape generated for text {text_id}")
            return None
    
    except Exception as e:
        logger.error(f"Error generating background music prompt: {str(e)}")
        return None

def update_text_with_music_prompt(db: Session, text_id: int, music_prompt: str) -> bool:
    """
    Update the Text model to include the background music prompt.
    
    Args:
        db: Database session
        text_id: ID of the text
        music_prompt: The generated music prompt to store
        
    Returns:
        Boolean indicating success
    """
    try:
        # Get the text from the database
        db_text = crud.get_text(db, text_id)
        if not db_text:
            logger.error(f"Text with ID {text_id} not found")
            return False
        
        # Update the background music prompt
        db_text.background_music_prompt = music_prompt
        db.commit()
        
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
def generate_background_music(db: Session, text_id: int) -> bool:
    """
    Phase 2: Generate background music using Replicate webhook for a text by ID.
    
    Args:
        db: Database session
        text_id: ID of the text to generate background music for
        
    Returns:
        True if webhook was successfully triggered, False otherwise.
    """
    from services.replicate_audio import create_webhook_prediction, ReplicateAudioConfig
    
    try:
        # Get the background music prompt from the database
        db_text = crud.get_text(db, text_id)
        if not db_text or not db_text.background_music_prompt:
            logger.error(f"Text with ID {text_id} not found or has no background music prompt")
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
        
        # Trigger webhook prediction and return immediately
        prediction_id = create_webhook_prediction("background_music", text_id, config)
        if prediction_id:
            logger.info(f"Background music generation webhook triggered for text {text_id}, prediction ID: {prediction_id}")
            crud.create_log(
                db=db,
                text_id=text_id,
                operation="background_music_generation_webhook_trigger",
                status="success",
                response={"prediction_id": prediction_id, "message": "Webhook triggered successfully"}
            )
            return True
        else:
            logger.error(f"Failed to trigger background music generation webhook for text {text_id}")
            crud.create_log(
                db=db,
                text_id=text_id,
                operation="background_music_generation_webhook_trigger",
                status="error",
                response={"error": "Failed to trigger webhook"}
            )
            return False

    except Exception as e:
        logger.error(f"Error triggering background music generation webhook: {str(e)}")
        crud.create_log(db=db, text_id=text_id, operation="background_music_generation_webhook_trigger", status="error", response={"error": str(e)})
        return False

@time_it("background_music_processing")
def process_background_music_for_text(db: Session, text_id: int) -> Tuple[bool, Optional[str], bool]:
    """
    Complete end-to-end background music processing using unified audio analysis:
    1. Generate a prompt with unified analysis
    2. Generate music with Replicate using the prompt and store in DB
    
    Args:
        db: Database session
        text_id: ID of the text to process
        
    Returns:
        Tuple of (prompt_success, music_prompt_or_none, music_generation_success)
    """
    from services.audio_analysis import analyze_text_for_audio
    
    # First check if the text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        logger.error(f"Text with ID {text_id} not found")
        return False, None, False
    
    # Check if music already exists and log it
    has_existing_prompt = bool(db_text.background_music_prompt)
    has_existing_audio = bool(db_text.background_music_audio_b64)
    
    if has_existing_prompt or has_existing_audio:
        logger.info(f"Text ID {text_id} already has background music prompt: {has_existing_prompt}, audio: {has_existing_audio}. Will overwrite.")
    
    try:
        # Phase 1: Generate prompt using unified analysis
        soundscape, _ = analyze_text_for_audio(db, text_id)
        if not soundscape:
            logger.error(f"No soundscape generated for text {text_id}")
            return False, None, False
        
        # Store the prompt
        update_text_with_music_prompt(db, text_id, soundscape)
        
        # Phase 2: Generate music and store in DB
        music_generated_and_stored = generate_background_music(db, text_id)
        if not music_generated_and_stored:
            return True, soundscape, False
        
        # Verify that the music was actually stored
        db.refresh(db_text)
        if not db_text.background_music_audio_b64:
            logger.error(f"Background music generation reported success but audio is not in database for text ID {text_id}")
            return True, soundscape, False
        
        return True, soundscape, True
        
    except Exception as e:
        logger.error(f"Error in background music processing: {e}")
        return False, None, False 

# New async versions for parallel processing
@time_it("async_background_music_generation")
async def generate_background_music_async(db: Session, text_id: int) -> bool:
    """
    Async version of generate_background_music for parallel processing.
    
    Args:
        db: Database session
        text_id: ID of the text to generate background music for
        
    Returns:
        True if music was generated and stored in DB successfully, False otherwise.
    """
    import asyncio
    
    # Run the synchronous function in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_background_music, db, text_id)

@time_it("async_background_music_processing")
async def process_background_music_for_text_async(db: Session, text_id: int) -> Tuple[bool, Optional[str], bool]:
    """
    Async version of process_background_music_for_text for parallel processing.
    
    Args:
        db: Database session
        text_id: ID of the text to process
        
    Returns:
        Tuple of (prompt_success, music_prompt_or_none, music_generation_success)
    """
    import asyncio
    
    # Run the synchronous function in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, process_background_music_for_text, db, text_id) 