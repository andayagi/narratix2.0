import asyncio
import time
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from utils.config import settings
from utils.logging import get_logger
from utils.http_client import get_async_client
from db import crud
from utils.timing import time_it

# Import Hume SDK
from hume import HumeClient
from hume.tts import FormatMp3, PostedUtterance, PostedUtteranceVoiceWithId, PostedContextWithUtterances

# Initialize logger
logger = get_logger(__name__)

# Maximum number of retries for API calls
MAX_RETRIES = 3
# Delay between retries in seconds
RETRY_DELAY = 5

@time_it("speech_generation")
async def generate_text_audio(db: Session, text_id: int) -> bool:
    """
    Generate audio for all segments of a text with parallel batch processing
    and store individual audio data in the DB.
    
    Args:
        db: Database session
        text_id: Text ID
        
    Returns:
        True if all segments were processed successfully, False otherwise.
    """
    
    # Invalidate existing force alignment data before speech generation
    db_text = crud.get_text(db, text_id)
    if db_text and db_text.word_timestamps:
        logger.info(f"Invalidating existing force alignment for text {text_id}")
        crud.clear_text_word_timestamps(db, text_id)
        logger.info(f"Cleared existing force alignment data for text {text_id}")
    
    # Get voice map for all characters
    characters = crud.get_characters_by_text(db, text_id)
    voice_map = {str(char.id): char.provider_id for char in characters if char.provider_id}
    
    # Get all segments in their natural order
    segments = crud.get_segments_by_text(db, text_id)
    if not segments:
        logger.warning(f"No segments found for text {text_id}")
        return False
    
    # Create logging entry
    log_operation = "parallel_batched_speech_generation"
    log_context = {"text_id": str(text_id), "segment_count": len(segments)}
    logger_contextual = get_logger(__name__, log_context)
    logger_contextual.info(f"Starting {log_operation} for text {text_id} with {len(segments)} segments")
    
    # Initialize Hume client once
    try:
        # Use default Hume client without custom httpx client to avoid async issues
        hume_client = HumeClient(api_key=settings.HUME_API_KEY)
        http_client = None  # Not using custom client
    except Exception as e:
        logger_contextual.error(f"Failed to initialize Hume client: {str(e)}", exc_info=True)
        return False
    
    batch_size = 5  # Maximum generations per request
    all_segments_processed_successfully = True
    
    # Create batch tasks for parallel processing
    batch_tasks = []
    
    for batch_start in range(0, len(segments), batch_size):
        batch_end = min(batch_start + batch_size, len(segments))
        batch_segments = segments[batch_start:batch_end]
        
        # Create task for this batch
        task = process_batch(
            db=db,
            segments=segments,
            batch_segments=batch_segments,
            batch_start=batch_start,
            batch_end=batch_end,
            voice_map=voice_map,
            hume_client=hume_client,
            logger_contextual=logger_contextual
        )
        batch_tasks.append(task)
    
    # Execute all batches in parallel
    try:
        logger_contextual.info(f"Starting parallel processing of {len(batch_tasks)} batches")
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Process results
        successful_batches = 0
        failed_batches = 0
        
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger_contextual.error(f"Batch {i} failed with exception: {result}", exc_info=True)
                all_segments_processed_successfully = False
                failed_batches += 1
            elif result:
                successful_batches += 1
            else:
                logger_contextual.warning(f"Batch {i} completed but with errors")
                all_segments_processed_successfully = False
                failed_batches += 1
        
        logger_contextual.info(f"Parallel batch processing completed: {successful_batches} successful, {failed_batches} failed")
        
    except Exception as e:
        logger_contextual.error(f"Error in parallel batch processing: {str(e)}", exc_info=True)
        all_segments_processed_successfully = False
    
    # No custom httpx client to close since we're using Hume's default client
    logger_contextual.info(f"Speech generation completed for text_id {text_id}")
        
    return all_segments_processed_successfully

async def process_batch(
    db: Session,
    segments: List,
    batch_segments: List,
    batch_start: int,
    batch_end: int,
    voice_map: Dict[str, str],
    hume_client: HumeClient,
    logger_contextual
) -> bool:
    """
    Process a single batch of segments with continuation context.
    
    Args:
        db: Database session
        segments: All segments (for context creation)
        batch_segments: Segments in this batch
        batch_start: Starting index of this batch
        batch_end: Ending index of this batch
        voice_map: Mapping of character IDs to voice IDs
        hume_client: Hume client instance
        logger_contextual: Contextual logger
        
    Returns:
        True if batch was processed successfully, False otherwise.
    """
    
    # Create context from previous batch segments for continuation
    context = None
    if batch_start > 0:
        # Use last 2-3 segments from previous batches as context
        context_start = max(0, batch_start - 3)
        context_segments = segments[context_start:batch_start]
        
        context_utterances = []
        for seg in context_segments:
            voice_id = voice_map.get(str(seg.character_id))
            if voice_id:
                context_utterances.append(PostedUtterance(
                    text=seg.text,
                    description=seg.description,
                    voice=PostedUtteranceVoiceWithId(id=voice_id, provider="CUSTOM_VOICE")
                ))
        
        if context_utterances:
            context = PostedContextWithUtterances(utterances=context_utterances)
            logger_contextual.info(f"Created continuation context with {len(context_utterances)} segments for batch {batch_start}-{batch_end}")
    
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
        return False
    
    # Generate audio for the batch with retry mechanism
    retry_count = 0
    last_exception = None
    batch_generated_successfully = False

    while retry_count < MAX_RETRIES:
        try:
            logger_contextual.info(f"Generating audio for batch {batch_start}-{batch_end} (attempt {retry_count + 1})")
            
            # Generate with continuation context for narrative coherence
            api_params = {
                "utterances": utterances,
                "format": FormatMp3(),
                "strip_headers": True
            }
            
            # Add context for batches after the first
            if context:
                api_params["context"] = context
            
            response = hume_client.tts.synthesize_json(**api_params)
            
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
                                    return False
                            else:
                                logger_contextual.error(f"Snippet group {snippet_group_idx} is empty for segment {segment.id}")
                                return False
                        else:
                            logger_contextual.warning(f"More snippet groups ({len(generation.snippets)}) than batch segments ({len(batch_segments)})")
                    
                    # If we have fewer snippet groups than segments, that's an error
                    if len(generation.snippets) < len(batch_segments):
                        logger_contextual.error(f"Received {len(generation.snippets)} snippet groups but expected {len(batch_segments)} for batch segments")
                        return False
                    
                    batch_generated_successfully = True
                else:
                    logger_contextual.error(f"No snippets found in response for batch {batch_start}-{batch_end}")
                    return False
            else:
                logger_contextual.error(f"No generations found in response for batch {batch_start}-{batch_end}")
                return False
            break
            
        except Exception as e:
            retry_count += 1
            last_exception = e
            logger_contextual.warning(f"Batch {batch_start}-{batch_end} generation attempt {retry_count} failed: {str(e)}")
            
            if retry_count >= MAX_RETRIES:
                logger_contextual.error(f"Error generating audio for batch {batch_start}-{batch_end} after {MAX_RETRIES} attempts: {str(last_exception)}", exc_info=True)
                return False
                
            await asyncio.sleep(RETRY_DELAY)
    
    return batch_generated_successfully

# Backward compatibility wrapper for synchronous calls
@time_it("speech_generation_sync")
def generate_text_audio_sync(db: Session, text_id: int) -> bool:
    """
    Synchronous wrapper for generate_text_audio.
    Maintains backward compatibility with existing synchronous code.
    """
    return asyncio.run(generate_text_audio(db, text_id))
        