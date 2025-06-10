import os
import time
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from utils.config import Settings
from utils.logging import get_logger
from db import crud, models

# Import the Hume SDK client
from hume import AsyncHumeClient
from hume.tts import PostedUtterance

# Initialize logger
logger = get_logger(__name__)

# Maximum number of retries for API calls
MAX_RETRIES = 3
# Delay between retries in seconds
RETRY_DELAY = 1

async def generate_character_voice(
    db: Session, 
    character_id: int, 
    character_name: str, 
    character_description: str,
    character_intro_text: str,
    text_id: int
) -> Optional[str]:
    """
    Generate and save a voice for a character using Hume AI.
    Only generates voices for characters that have assigned segments.
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
            async for chunk in tts_stream:
                if hasattr(chunk, "generation_id"):
                    generation_id = chunk.generation_id
                    break

            if not generation_id:
                raise ValueError("Missing 'generation_id' in API response stream")

            # Step 2: Save the generated voice with naming format [name]_[text_id]
            voice_name = f"{character_name}_{text_id}"
            
            save_response = await hume_client.tts.voices.create(
                name=voice_name,
                generation_id=generation_id
            )
            
            # Get the voice ID from the response
            voice_id = save_response.id

            # Save provider_id and provider to the database
            crud.update_character_voice(db, character_id, voice_id, provider="HUME")
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