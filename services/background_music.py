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
from db import crud, models

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# Initialize logger
logger = get_logger(__name__)

def generate_background_music_prompt(db: Session, text_id: int) -> Optional[str]:
    """
    Generate a background music prompt using Claude for a text by ID.
    
    Args:
        db: Database session
        text_id: ID of the text to generate background music for
        
    Returns:
        The generated background music prompt, or None if error
    """
    # Get text content from database
    db_text = crud.get_text(db, text_id)
    if not db_text:
        logger.error(f"Text with ID {text_id} not found")
        return None
    
    text_content = db_text.content
    
    # Log full Anthropic API request
    logger.info("Anthropic API Request for background music", extra={"anthropic_request": {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 536,
        "temperature": 0.7,
        "system": "output only what was asked, no explanatory text",
        "messages": [{"role": "user", "content": f"Describe in a short paragraph (60 words) the background audio\\music for this text. mention the genre of the book. Focus on concrete instructions like background noises, tempo, instrumentation (if any), rhythm, and musical motifs. \n1-2 sentences.\n{text_content}"}]
    }})
    
    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=536,
            temperature=0.7,
            system="output only what was asked, no explanatory text ",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Describe in a short paragraph (60 words) the background audio\\music for this text. mention the genre of the book. Focus on concrete instructions like background noises, tempo, instrumentation (if any), rhythm, and musical motifs. \n1-2 sentences.\n{text_content}"
                        }
                    ]
                }
            ])
        
        # Log full Anthropic API response
        logger.info("Anthropic API Response for background music", extra={"anthropic_response": response.content})
        
        # Extract the prompt from the response
        music_prompt = response.content[0].text
        
        # Store the prompt in the database
        update_text_with_music_prompt(db, text_id, music_prompt)
        
        return music_prompt
    
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

def generate_background_music(db: Session, text_id: int) -> bool:
    """
    Phase 2: Generate background music using Replicate for a text by ID and store in DB.
    
    Args:
        db: Database session
        text_id: ID of the text to generate background music for
        
    Returns:
        True if music was generated and stored in DB successfully, False otherwise.
    """
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
        
        audio_file_for_duration_calc = None
        temp_audio_file = None
        
        # Check for segments with audio_data_b64
        import tempfile
        
        for segment in segments:
            if segment.audio_data_b64:
                # Found a segment with base64 audio data, create a temporary file
                try:
                    audio_bytes = base64.b64decode(segment.audio_data_b64)
                    fd, temp_path = tempfile.mkstemp(suffix='.mp3')
                    os.close(fd)
                    
                    with open(temp_path, 'wb') as f:
                        f.write(audio_bytes)
                    
                    temp_audio_file = temp_path
                    audio_file_for_duration_calc = temp_path
                    logger.info(f"Created temporary audio file from segment {segment.id} audio_data_b64")
                    break
                except Exception as temp_file_error:
                    logger.error(f"Error creating temporary file from audio_data_b64: {str(temp_file_error)}")
                    # Continue to next segment if this one fails
                    continue
        
        if not audio_file_for_duration_calc:
            logger.error(f"No audio_data_b64 found for any segments of text with ID {text_id} to calculate duration.")
            return False
            
        try:
            audio_duration = get_audio_duration(audio_file_for_duration_calc)
            if audio_duration <= 0:
                logger.error(f"Could not determine audio duration for file {audio_file_for_duration_calc}")
                return False
            
            # Calculate sum of trailing_silence from all segments
            total_trailing_silence = sum(segment.trailing_silence for segment in segments if segment.trailing_silence)
            
            music_duration = int(audio_duration) + total_trailing_silence + 6
            
            logger.info(f"Generating background music with prompt: {music_prompt}", extra={"music_prompt": music_prompt, "duration": music_duration})
            
            output_url = replicate.run(
                "ardianfe/music-gen-fn-200e:96af46316252ddea4c6614e31861876183b59dce84bad765f38424e87919dd85",
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
            
            if not output_url:
                logger.error("No output URL received from Replicate API")
                crud.create_log(db=db, text_id=text_id, operation="background_music_generation_db", status="error", response={"error": "No output URL from Replicate"})
                return False
            
            import requests
            
            # Download the music data
            response = requests.get(output_url)
            response.raise_for_status()
            audio_bytes = response.content
            
            # Encode to base64
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            # Store base64 audio in the database using CRUD function
            updated_text = crud.update_text_background_music_audio(db, text_id, audio_base64)
            if updated_text:
                logger.info(f"Successfully generated and stored background music in DB for text {text_id}")
                crud.create_log(
                    db=db,
                    text_id=text_id,
                    operation="background_music_generation_db",
                    status="success",
                    response={"message": "Background music stored in DB"}
                )
                return True
            else:
                logger.error(f"Failed to update text with ID {text_id} with background music audio")
                crud.create_log(
                    db=db,
                    text_id=text_id,
                    operation="background_music_generation_db",
                    status="error",
                    response={"error": "Failed to update text with background music audio"}
                )
                return False
        finally:
            # Clean up temporary file if created
            if temp_audio_file and os.path.exists(temp_audio_file):
                try:
                    os.remove(temp_audio_file)
                    logger.info(f"Removed temporary audio file: {temp_audio_file}")
                except Exception as cleanup_error:
                    logger.error(f"Error removing temporary file: {str(cleanup_error)}")

    except requests.exceptions.RequestException as req_e:
        logger.error(f"Error downloading background music from Replicate: {str(req_e)}")
        crud.create_log(db=db, text_id=text_id, operation="background_music_generation_db", status="error", response={"error": f"Replicate download error: {str(req_e)}"})
        return False
    except Exception as e:
        logger.error(f"Error generating background music and storing in DB: {str(e)}")
        crud.create_log(
            db=db,
            text_id=text_id,
            operation="background_music_generation_db",
            status="error",
            response={"error": str(e)}
        )
        return False

def process_background_music_for_text(db: Session, text_id: int) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Complete end-to-end background music processing:
    1. Generate a prompt with Claude
    2. Generate music with Replicate using the prompt and store in DB
    
    Args:
        db: Database session
        text_id: ID of the text to process
        
    Returns:
        Tuple of (prompt_success, music_prompt_or_none, music_generation_success)
    """
    # Phase 1: Generate prompt
    music_prompt = generate_background_music_prompt(db, text_id)
    if not music_prompt:
        return False, None, False
    
    # Phase 2: Generate music and store in DB
    music_generated_and_stored = generate_background_music(db, text_id)
    if not music_generated_and_stored:
        return True, music_prompt, False
    
    return True, music_prompt, True 