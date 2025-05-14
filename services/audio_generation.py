import os
import json
import base64  # Add base64 import for decoding
import subprocess
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from utils.config import settings
from utils.logging import get_logger
from utils.http_client import create_client  # Import the centralized HTTP client
from db import crud

# Import Hume SDK
from hume import HumeClient
from hume.tts import FormatMp3, PostedUtterance, PostedUtteranceVoiceWithId

# Initialize logger
logger = get_logger(__name__)

# Maximum number of retries for API calls
MAX_RETRIES = 3
# Delay between retries in seconds
RETRY_DELAY = 5  # Increased from 1 to 5
# Timeout for HTTP requests in seconds (100 minutes)
HTTP_TIMEOUT = 6000.0

def generate_text_audio(db: Session, text_id: str) -> str:
    """
    Generate audio for all segments of a text using Hume AI's batch API
    
    Args:
        db: Database session
        text_id: Text ID
        
    Returns:
        Path to the generated audio file
    """
    
    # Get voice map for all characters
    characters = crud.get_characters_by_text(db, text_id)
    voice_map = {str(char.id): char.provider_id for char in characters if char.provider_id}
    
    # Get all segments
    segments = crud.get_segments_by_text(db, text_id)
    if not segments:
        logger.warning(f"No segments found for text {text_id}")
        return None
    
    # Create logging entry
    log_operation = "batch_audio_generation"
    log_context = {"text_id": str(text_id), "segment_count": len(segments)}
    logger = get_logger(__name__, log_context)
    logger.info(f"Starting {log_operation} for text {text_id} with {len(segments)} segments")
    
    # Generate file path
    file_name = f"text_{text_id}.mp3"
    file_path = os.path.join(settings.AUDIO_STORAGE_PATH, file_name)
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Prepare utterances for Hume API
    utterances = []
    for segment in segments:
        voice_id = voice_map.get(str(segment.character_id))
        if not voice_id:
            logger.warning(f"No voice ID found for character {segment.character_id} in segment {segment.id}")
            continue
        
        # Prepare parameters for utterance
        utterance_params = {
            "text": segment.text,
            "description": segment.description,
            "voice": PostedUtteranceVoiceWithId(id=voice_id, provider="CUSTOM_VOICE")
        }
        
        # Add optional parameters
        #if segment.speed is not None:
        #    utterance_params["speed"] = segment.speed
        #if segment.trailing_silence is not None:
        #    utterance_params["trailing_silence"] = segment.trailing_silence
            
        # Create utterance with all parameters at once
        utterance = PostedUtterance(**utterance_params)
        utterances.append(utterance)
    
    # Stop process if no utterances were created
    if not utterances:
        logger.error(f"No valid utterances found for text {text_id}. Cannot generate audio.")
        return None
    
    # Add retry mechanism
    retry_count = 0
    last_exception = None
    
    while retry_count < MAX_RETRIES:
        try:
            # Create a new client instance for each attempt to avoid connection reuse issues
            # Use a custom HTTP client with extended timeout
            import httpx
            http_client = httpx.Client(timeout=httpx.Timeout(HTTP_TIMEOUT))
            hume_client = HumeClient(api_key=settings.HUME_API_KEY, httpx_client=http_client)
            
            logger.info(f"Sending request to Hume API with {len(utterances)} utterances (attempt {retry_count + 1})")
            logger.info(f"Using extended timeout of {HTTP_TIMEOUT} seconds")
            response = hume_client.tts.synthesize_json(
                utterances=utterances,
                format=FormatMp3(),
                strip_headers=True
            )
            
            # Write the audio file
            with open(file_path, "wb") as f:
                # Decode the audio string to bytes before writing
                audio_bytes = base64.b64decode(response.generations[0].audio)
                f.write(audio_bytes)
            
            logger.info(f"Successfully generated audio file: {file_path}")
            
            # Update all segments with the audio file path
            for segment in segments:
                crud.update_segment_audio(db, segment.id, file_path)
            
            return file_path
            
        except Exception as e:
            retry_count += 1
            last_exception = e
            # Log the attempt
            logger.warning(f"Audio generation attempt {retry_count} failed: {str(e)}")
            
            if retry_count >= MAX_RETRIES:
                # Log the exception with our regular logger after all retries
                logger.error(f"Error generating audio after {retry_count} attempts: {str(e)}", exc_info=True)
                break
                
            # Wait before retrying
            import time
            time.sleep(RETRY_DELAY)
    
    # If we get here, all retries failed
    raise last_exception

def get_audio_for_text(db: Session, text_id: str) -> Optional[str]:
    """
    Get the audio file path for a text
    
    Args:
        db: Database session
        text_id: Text ID
        
    Returns:
        Path to the audio file, or None if not generated
    """
    
    # Get all segments
    segments = crud.get_segments_by_text(db, text_id)
    
    # Check if any segment has an audio file
    for segment in segments:
        if segment.audio_file:
            return segment.audio_file
    
    return None

def combine_audio_with_background(narration_audio: str, background_music: str, bg_volume: float = 0.1) -> Optional[str]:
    """
    Mix narration audio with background music using ffmpeg.
    
    Args:
        narration_audio: Path to the narration audio file
        background_music: Path to the background music file
        bg_volume: Volume level for background music (0.1 = 10%)
        
    Returns:
        Path to the combined audio file, or None if error
    """
    try:
        # Generate output file path
        output_dir = os.path.dirname(narration_audio)
        base_filename = os.path.basename(narration_audio)
        output_filename = f"mixed_{base_filename}"
        output_path = os.path.join(output_dir, output_filename)
        
        # Log the operation
        logger.info(f"Combining audio {narration_audio} with background music {background_music}")
        
        # Use ffmpeg to mix the audio files
        cmd = [
            'ffmpeg',
            '-i', narration_audio,
            '-stream_loop', '-1',  # Loop background music indefinitely
            '-i', background_music,
            '-filter_complex',
            f'[1:a]volume={bg_volume}[bg];[0:a][bg]amix=inputs=2:duration=first',
            '-c:a', 'libmp3lame',
            '-q:a', '2',
            '-y',  # Overwrite output file if it exists
            output_path
        ]
        
        # Run the ffmpeg command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Error combining audio: {result.stderr}")
            return None
        
        logger.info(f"Successfully created mixed audio: {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Error combining audio with background music: {str(e)}")
        return None