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
    Generate audio for all segments of a text with batched processing
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
    log_operation = "batched_speech_generation"
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
    batch_size = 5  # Maximum generations per request
    
    # Process segments in batches
    for batch_start in range(0, len(segments), batch_size):
        batch_end = min(batch_start + batch_size, len(segments))
        batch_segments = segments[batch_start:batch_end]
        
        # Create utterances for the batch
        utterances = []
        batch_voice_ids = []
        
        for segment in batch_segments:
            voice_id = voice_map.get(str(segment.character_id))
            if not voice_id:
                logger_contextual.warning(f"No voice ID found for character {segment.character_id} in segment {segment.id}")
                continue
            
            batch_voice_ids.append(voice_id)
            
            # Prepare utterance for Hume API
            utterance_params = {
                "text": segment.text,
                "description": segment.description,
                "voice": PostedUtteranceVoiceWithId(id=voice_id, provider="CUSTOM_VOICE")
            }
            
            # Add optional parameters from segment if they exist
            if hasattr(segment, 'trailing_silence') and segment.trailing_silence is not None:
                utterance_params["trailing_silence"] = segment.trailing_silence
                
            # Create utterance with all parameters
            utterances.append(PostedUtterance(**utterance_params))
        
        if not utterances:
            logger_contextual.warning(f"No valid utterances in batch {batch_start}-{batch_end}")
            all_segments_processed_successfully = False
            continue
        
        # Generate audio for the batch with retry mechanism
        retry_count = 0
        last_exception = None
        batch_generated_successfully = False

        while retry_count < MAX_RETRIES:
            try:
                logger_contextual.info(f"Generating audio for batch {batch_start}-{batch_end} (attempt {retry_count + 1})")
                
                # Generate without continuation context to avoid glitches
                response = hume_client.tts.synthesize_json(
                    utterances=utterances,
                    format=FormatMp3(),
                    strip_headers=True
                )
                
                # Process each audio snippet from the batch response
                if response.generations and len(response.generations) > 0:
                    generation = response.generations[0]
                    logger_contextual.info(f"Generation response has {len(response.generations)} generations")
                    
                    if hasattr(generation, 'snippets') and generation.snippets:
                        logger_contextual.info(f"Generation has {len(generation.snippets)} snippet groups")
                        
                        # Each utterance creates its own snippet group
                        for snippet_group_idx, snippet_group in enumerate(generation.snippets):
                            if snippet_group_idx < len(batch_segments):
                                segment = batch_segments[snippet_group_idx]
                                
                                # Each snippet group should have one snippet for that utterance
                                if len(snippet_group) > 0:
                                    snippet = snippet_group[0]  # First snippet in this group
                                    audio_bytes_b64 = snippet.audio
                                    
                                    logger_contextual.info(f"Processing snippet group {snippet_group_idx} for segment {segment.id}")
                                    
                                    if audio_bytes_b64:
                                        crud.update_segment_audio_data(db, segment.id, audio_bytes_b64)
                                        logger_contextual.info(f"Successfully generated audio for segment {segment.id}")
                                    else:
                                        logger_contextual.error(f"No audio data returned for segment {segment.id}")
                                        all_segments_processed_successfully = False
                                else:
                                    logger_contextual.error(f"Snippet group {snippet_group_idx} is empty for segment {segment.id}")
                                    all_segments_processed_successfully = False
                            else:
                                logger_contextual.warning(f"More snippet groups ({len(generation.snippets)}) than batch segments ({len(batch_segments)})")
                        
                        # If we have fewer snippet groups than segments, that's an error
                        if len(generation.snippets) < len(batch_segments):
                            logger_contextual.error(f"Received {len(generation.snippets)} snippet groups but expected {len(batch_segments)} for batch segments")
                            all_segments_processed_successfully = False
                        
                        # Store generation ID for next batch's continuation
                        previous_generation_id = generation.generation_id
                        logger_contextual.info(f"Saved generation ID {previous_generation_id} for next batch")
                        batch_generated_successfully = True
                    else:
                        logger_contextual.error(f"No snippets found in response for batch {batch_start}-{batch_end}")
                        all_segments_processed_successfully = False
                else:
                    logger_contextual.error(f"No generations found in response for batch {batch_start}-{batch_end}")
                    all_segments_processed_successfully = False
                break
                
            except Exception as e:
                retry_count += 1
                last_exception = e
                logger_contextual.warning(f"Batch {batch_start}-{batch_end} generation attempt {retry_count} failed: {str(e)}")
                
                if retry_count >= MAX_RETRIES:
                    logger_contextual.error(f"Error generating audio for batch {batch_start}-{batch_end} after {MAX_RETRIES} attempts: {str(last_exception)}", exc_info=True)
                    all_segments_processed_successfully = False
                    break
                    
                time.sleep(RETRY_DELAY)
        
        if not batch_generated_successfully:
            all_segments_processed_successfully = False

    # Close the httpx client when done with all operations for this text_id
    if 'http_client' in locals() and http_client:
        try:
            http_client.close()
            logger_contextual.info(f"Closed httpx client for text_id {text_id}")
        except Exception as e_close:
            logger_contextual.warning(f"Error closing httpx client for text_id {text_id}: {str(e_close)}")
        
    return all_segments_processed_successfully
        