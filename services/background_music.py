import replicate
from anthropic import Anthropic
import json
import os
import subprocess
from typing import Dict, Any, Optional, Tuple
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

def generate_background_music(db: Session, text_id: int) -> Optional[str]:
    """
    Phase 2: Generate background music using Replicate for a text by ID.
    
    Args:
        db: Database session
        text_id: ID of the text to generate background music for
        
    Returns:
        Path to the generated background music file, or None if error
    """
    try:
        # Get the background music prompt from the database
        db_text = crud.get_text(db, text_id)
        if not db_text or not db_text.background_music_prompt:
            logger.error(f"Text with ID {text_id} not found or has no background music prompt")
            return None
        
        music_prompt = db_text.background_music_prompt
        
        # Get segments to calculate required duration
        segments = crud.get_segments_by_text(db, text_id)
        if not segments:
            logger.error(f"No segments found for text with ID {text_id}")
            return None
        
        # Find the audio file path from segments
        audio_file = None
        for segment in segments:
            if segment.audio_file:
                audio_file = segment.audio_file
                break
        
        if not audio_file:
            logger.error(f"No audio file found for any segments of text with ID {text_id}")
            return None
        
        # Get audio duration and add 6 seconds
        audio_duration = get_audio_duration(audio_file)
        if audio_duration <= 0:
            logger.error(f"Could not determine audio duration for file {audio_file}")
            return None
        
        # Duration = audio duration + 6 seconds
        music_duration = int(audio_duration) + 6
        
        # Generate background music using Replicate
        logger.info(f"Generating background music with prompt: {music_prompt}", extra={"music_prompt": music_prompt, "duration": music_duration})
        
        # Call Replicate API
        output = replicate.run(
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
        
        if not output:
            logger.error("No output received from Replicate API")
            return None
        
        # Download the generated music file
        import requests
        from pathlib import Path
        
        # Create background music directory if it doesn't exist
        bg_music_dir = os.path.join(settings.AUDIO_STORAGE_PATH, "background_music")
        os.makedirs(bg_music_dir, exist_ok=True)
        
        # Define output file path
        output_file = os.path.join(bg_music_dir, f"bg_music_text_{text_id}.mp3")
        
        # Download the file
        response = requests.get(output)
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        logger.info(f"Successfully generated background music: {output_file}")
        
        # Log the operation
        crud.create_log(
            db=db,
            text_id=text_id,
            operation="background_music_generation",
            status="success",
            response={"music_file": output_file}
        )
        
        return output_file
    except Exception as e:
        logger.error(f"Error generating background music: {str(e)}")
        
        # Log the error
        crud.create_log(
            db=db,
            text_id=text_id,
            operation="background_music_generation",
            status="error",
            response={"error": str(e)}
        )
        
        return None

def process_background_music_for_text(db: Session, text_id: int) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Complete end-to-end background music processing:
    1. Generate a prompt with Claude
    2. Generate music with Replicate using the prompt
    
    Args:
        db: Database session
        text_id: ID of the text to process
        
    Returns:
        Tuple of (success, prompt, music_file_path)
    """
    # Phase 1: Generate prompt
    music_prompt = generate_background_music_prompt(db, text_id)
    if not music_prompt:
        return False, None, None
    
    # Phase 2: Generate music
    music_file = generate_background_music(db, text_id)
    if not music_file:
        return False, music_prompt, None
    
    return True, music_prompt, music_file 