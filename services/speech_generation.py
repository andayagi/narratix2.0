import time
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
import httpx

from utils.config import settings
from utils.logging import get_logger
from db import crud

# Import Hume SDK
from hume import HumeClient
from hume.tts import FormatMp3, PostedUtterance, PostedUtteranceVoiceWithId, PostedContextWithGenerationId

# Initialize logger
logger = get_logger(__name__)

# Maximum number of retries for API calls
MAX_RETRIES = 3
# Delay between retries in seconds
RETRY_DELAY = 5
# Timeout for HTTP requests in seconds (100 minutes)
HTTP_TIMEOUT = 6000.0

def generate_text_audio(db: Session, text_id: int) -> bool:
    """
    Generate audio for all segments of a text with sequential continuation
    and store individual audio data in the DB.
    
    Args:
        db: Database session
        text_id: Text ID
        
    Returns:
        True if all segments were processed successfully, False otherwise.
    """
    
    # Get voice map for all characters
    characters = crud.get_characters_by_text(db, text_id)
    voice_map = {str(char.id): char.provider_id for char in characters if char.provider_id}
    
    # Get all segments in their natural order
    segments = crud.get_segments_by_text(db, text_id)
    if not segments:
        logger.warning(f"No segments found for text {text_id}")
        return False
    
    # Create logging entry
    log_operation = "sequential_continuation_speech_generation"
    log_context = {"text_id": str(text_id), "segment_count": len(segments)}
    logger_contextual = get_logger(__name__, log_context)
    logger_contextual.info(f"Starting {log_operation} for text {text_id} with {len(segments)} segments")
    
    # Initialize Hume and HTTP clients once
    try:
        http_client = httpx.Client(timeout=httpx.Timeout(HTTP_TIMEOUT))
        hume_client = HumeClient(api_key=settings.HUME_API_KEY, httpx_client=http_client)
    except Exception as e:
        logger_contextual.error(f"Failed to initialize Hume client: {str(e)}", exc_info=True)
        return False
    
    all_segments_processed_successfully = True
    previous_generation_id = None
    
    for i, segment in enumerate(segments):
        voice_id = voice_map.get(str(segment.character_id))
        if not voice_id:
            logger_contextual.warning(f"No voice ID found for character {segment.character_id} in segment {segment.id}")
            continue
    
        # Prepare utterance for Hume API
        utterance_params = {
            "text": segment.text,
            "description": segment.description,
            "voice": PostedUtteranceVoiceWithId(id=voice_id, provider="CUSTOM_VOICE")
        }
        
        # Add optional parameters from segment if they exist
        if hasattr(segment, 'speed') and segment.speed is not None:
            utterance_params["speed"] = segment.speed
        if hasattr(segment, 'trailing_silence') and segment.trailing_silence is not None:
            utterance_params["trailing_silence"] = segment.trailing_silence
            
        # Create utterance with all parameters
        utterance = PostedUtterance(**utterance_params)
        
        # Generate audio with retry mechanism
        retry_count = 0
        last_exception = None
        segment_generated_successfully = False

        while retry_count < MAX_RETRIES:
            try:
                logger_contextual.info(f"Generating audio for segment {segment.id} (attempt {retry_count + 1})")
                
                # Use previous generation ID for context if available
                if previous_generation_id:
                    logger_contextual.info(f"Using previous generation ID {previous_generation_id} for continuation")
                    response = hume_client.tts.synthesize_json(
                        utterances=[utterance],
                        format=FormatMp3(),
                        strip_headers=True,
                        context=PostedContextWithGenerationId(generation_id=previous_generation_id)
                    )
                else:
                    # First segment doesn't have context
                    response = hume_client.tts.synthesize_json(
                        utterances=[utterance],
                        format=FormatMp3(),
                        strip_headers=True
                    )
                
                # Get base64 encoded audio data from response
                audio_bytes_b64 = response.generations[0].audio
                
                # Store audio data in the database
                if audio_bytes_b64:
                    crud.update_segment_audio_data(db, segment.id, audio_bytes_b64)
                    logger_contextual.info(f"Successfully generated audio for segment {segment.id} and stored in DB.")
                    segment_generated_successfully = True
                    
                    # Store generation ID for next segment's continuation
                    previous_generation_id = response.generations[0].generation_id
                    logger_contextual.info(f"Saved generation ID {previous_generation_id} for next segment")
                else:
                    logger_contextual.error(f"No audio data returned for segment {segment.id}")
                    segment_generated_successfully = False
                break
                
            except Exception as e:
                retry_count += 1
                last_exception = e
                logger_contextual.warning(f"Segment {segment.id} generation attempt {retry_count} failed: {str(e)}")
                
                if retry_count >= MAX_RETRIES:
                    logger_contextual.error(f"Error generating audio for segment {segment.id} after {MAX_RETRIES} attempts: {str(last_exception)}", exc_info=True)
                    all_segments_processed_successfully = False # Mark failure for this segment
                    break
                    
                time.sleep(RETRY_DELAY)
        
        if not segment_generated_successfully:
            all_segments_processed_successfully = False # Mark failure if loop exited without success

    # Close the httpx client when done with all operations for this text_id
    if 'http_client' in locals() and http_client:
        try:
            http_client.close()
            logger_contextual.info(f"Closed httpx client for text_id {text_id}")
        except Exception as e_close:
            logger_contextual.warning(f"Error closing httpx client for text_id {text_id}: {str(e_close)}")
        
    return all_segments_processed_successfully
        