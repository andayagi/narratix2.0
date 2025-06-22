import os
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from utils.config import Settings
from utils.logging import get_logger
from db import crud, models
from utils.timing import time_it

# Import the Hume SDK client
from hume import AsyncHumeClient
from hume.tts import PostedUtterance

# Initialize logger
logger = get_logger(__name__)

# Maximum number of retries for API calls
MAX_RETRIES = 3
# Delay between retries in seconds
RETRY_DELAY = 1

@time_it("generate_character_voice")
async def generate_character_voice(
    db: Session, 
    character_id: int, 
    character_name: str, 
    character_description: str,
    character_intro_text: str,
    text_id: int,
    force_regenerate: bool = False
) -> Optional[str]:
    """
    Generate and save a voice for a character using Hume AI.
    Only generates voices for characters that have assigned segments.
    If force_regenerate is True, deletes existing voice before creating new one.
    """
    # Check if character has any segments
    segments = db.query(models.TextSegment).filter(models.TextSegment.character_id == character_id).all()
    if not segments:
        logger.info(f"Skipping voice generation for character {character_id} ({character_name}) - no assigned segments")
        return None
    
    # Ensure we're using the latest API key from environment
    current_settings = Settings()
    api_key = os.getenv("HUME_API_KEY") or current_settings.HUME_API_KEY
    
    # Initialize the Hume SDK client
    hume_client = AsyncHumeClient(api_key=api_key)
    
    # Step 2: Save the generated voice with naming format [name]_[text_id]
    voice_name = f"{character_name}_{text_id}"
    
    # If force_regenerate is True, delete existing voice first
    if force_regenerate:
        try:
            logger.info(f"Force regenerate enabled - deleting existing voice '{voice_name}' if it exists")
            await hume_client.tts.voices.delete(name=voice_name)
            logger.info(f"Successfully deleted existing voice '{voice_name}'")
        except Exception as e:
            # Voice might not exist or delete failed - continue with generation
            logger.info(f"Could not delete voice '{voice_name}' (might not exist): {str(e)}")
    
    # Get current character to check if voice already exists
    character = crud.get_character(db, character_id)
    if character and character.provider_id and not force_regenerate:
        logger.info(f"Character {character_name} already has voice {character.provider_id}, skipping generation")
        return character.provider_id
    
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            # Step 1: Generate speech to obtain generation_id
            tts_stream = hume_client.tts.synthesize_json_streaming(
                utterances=[
                    PostedUtterance(
                        text=character_intro_text,
                        description=character_description[:200]
                    )
                ]
            )
            
            generation_id = None
            chunk_count = 0
            async for chunk in tts_stream:
                chunk_count += 1
                # Check if chunk has generation_id attribute and it's not empty
                if hasattr(chunk, "generation_id") and chunk.generation_id:
                    generation_id = chunk.generation_id
                    logger.info(f"Found generation_id: {generation_id}")
                    break

            if not generation_id:
                # If no chunks were received, the content might be filtered. Try with fallback text.
                if chunk_count == 0:
                    logger.warning(f"No chunks received for character {character_name}, trying fallback text")
                    fallback_text = f"Hello, I am {character_name}."
                    fallback_stream = hume_client.tts.synthesize_json_streaming(
                        utterances=[
                            PostedUtterance(
                                text=fallback_text,
                                description=f"Character named {character_name}"
                            )
                        ]
                    )
                    
                    async for chunk in fallback_stream:
                        if hasattr(chunk, "generation_id") and chunk.generation_id:
                            generation_id = chunk.generation_id
                            logger.info(f"Found generation_id with fallback text: {generation_id}")
                            break
                
                if not generation_id:
                    raise ValueError("Missing 'generation_id' in API response stream")

            # Step 2: Save the generated voice (voice_name already defined above)
            save_response = await hume_client.tts.voices.create(
                name=voice_name,
                generation_id=generation_id
            )
            
            # Get the voice ID from the response
            voice_id = save_response.id

            # Save provider_id and provider to the database
            crud.update_character_voice(db, character_id, voice_id, provider="HUME")
            logger.info(f"Successfully created voice {voice_id} for character {character_name}")
            return voice_id
            
        except Exception as e:
            retry_count += 1
            # Log the attempt
            logger.warning(f"Voice generation attempt {retry_count} failed: {str(e)}")
            
            if retry_count >= MAX_RETRIES:
                # Log error with context after all retries have failed
                error_context = {
                    "operation": "voice_generation", 
                    "character_id": character_id, 
                    "text_id": text_id,
                    "attempts": retry_count
                }
                logger.error(f"Character voice generation failed after {retry_count} attempts: {str(e)}", exc_info=True)
                raise
                
            # Wait before retrying
            time.sleep(RETRY_DELAY)

@time_it("parallel_voice_generation")
async def generate_all_character_voices_parallel(db: Session, text_id: int) -> List[Tuple[int, Optional[str]]]:
    """
    Generate voices for all characters of a text in parallel.
    
    Args:
        db: Database session
        text_id: ID of the text to generate voices for
        
    Returns:
        List of tuples (character_id, voice_id_or_none) for each character
    """
    logger.info(f"Starting parallel voice generation for text {text_id}")
    
    # Get all characters for this text
    characters = crud.get_characters_by_text(db, text_id)
    if not characters:
        logger.warning(f"No characters found for text {text_id}")
        return []
    
    logger.info(f"Found {len(characters)} characters for parallel voice generation")
    
    # Create tasks for parallel voice generation
    voice_tasks = []
    character_info = []
    
    for character in characters:
        # Only create tasks for speaking characters with segments
        segments = db.query(models.TextSegment).filter(models.TextSegment.character_id == character.id).all()
        if not segments:
            logger.info(f"Skipping character {character.id} ({character.name}) - no assigned segments")
            continue
            
        character_info.append(character)
        task = generate_character_voice(
            db=db,
            character_id=character.id,
            character_name=character.name,
            character_description=character.description or f"Character named {character.name}",
            character_intro_text=character.intro_text or f"Hello, I am {character.name}.",
            text_id=text_id
        )
        voice_tasks.append(task)
    
    if not voice_tasks:
        logger.warning(f"No characters with segments found for text {text_id}")
        return []
    
    logger.info(f"Starting parallel generation of {len(voice_tasks)} character voices")
    
    # Execute all voice generation tasks in parallel
    try:
        voice_results = await asyncio.gather(*voice_tasks, return_exceptions=True)
        
        # Process results and log outcomes
        results = []
        successful_generations = 0
        failed_generations = 0
        
        for i, (character, result) in enumerate(zip(character_info, voice_results)):
            if isinstance(result, Exception):
                logger.error(f"Voice generation failed for character {character.id} ({character.name}): {result}")
                results.append((character.id, None))
                failed_generations += 1
            else:
                if result:
                    logger.info(f"Successfully generated voice for character {character.id} ({character.name}): {result}")
                    successful_generations += 1
                else:
                    logger.info(f"Voice generation skipped for character {character.id} ({character.name})")
                results.append((character.id, result))
        
        logger.info(f"Parallel voice generation completed for text {text_id}: {successful_generations} successful, {failed_generations} failed")
        return results
        
    except Exception as e:
        logger.error(f"Error in parallel voice generation for text {text_id}: {e}")
        return []