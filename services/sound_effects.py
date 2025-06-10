"""
Service for analyzing text, generating, and managing sound effects.

This service is designed to be completely independent of text analysis for speech generation.
It analyzes the full text content to identify opportunities for cinematic sound effects
and generates them using an AI audio generation service (AudioX).
"""
import re
import base64
import os
import json
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from gradio_client import Client
import anthropic

from utils.logging import get_logger
from utils.config import settings
from db import crud
from services.force_alignment import run_force_alignment

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=settings.ANTHROPIC_API_KEY,
)

logger = get_logger(__name__)

# Placeholder for an Anthropic client, assuming one will be available.
# from clients.anthropic_client import get_anthropic_client 

# Initialize AudioX client
AUDIOX_CLIENT = None

def get_audiox_client():
    """Get AudioX client instance, initializing if needed"""
    global AUDIOX_CLIENT
    if AUDIOX_CLIENT is None:
        try:
            AUDIOX_CLIENT = Client("Zeyue7/AudioX")
            logger.info("AudioX client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AudioX client: {e}")
            AUDIOX_CLIENT = None
    return AUDIOX_CLIENT

def delete_existing_sound_effects(db: Session, text_id: int) -> int:
    """
    Delete all existing sound effects for a given text_id.
    
    Args:
        db: Database session.
        text_id: The ID of the text to clean up.
        
    Returns:
        Number of deleted sound effects.
    """
    deleted_count = crud.delete_sound_effects_by_text(db, text_id)
    logger.info(f"Deleted {deleted_count} existing sound effects for text {text_id}")
    return deleted_count

def analyze_text_for_sound_effects(
    db: Session, 
    text_id: int
) -> List[Dict]:
    """
    Analyzes the complete text using force alignment data and LLM to identify sound effect opportunities.
    
    Args:
        db: Database session.
        text_id: The ID of the text to analyze.
        
    Returns:
        A list of sound effect specifications.
    """
    
    # Delete any existing sound effects for this text first
    delete_existing_sound_effects(db, text_id)
    
    text_obj = crud.get_text(db, text_id)
    if not text_obj:
        logger.error(f"Text with id {text_id} not found.")
        return []
        
    full_text = text_obj.content

    # Step 1: Get or generate force alignment data
    word_timestamps = None
    if text_obj.word_timestamps:
        logger.info(f"Using existing force alignment data for text {text_id}")
        word_timestamps = text_obj.word_timestamps
    else:
        logger.info(f"No force alignment data found for text {text_id}, generating...")
        success = run_force_alignment(db, text_id)
        if success:
            # Refresh the text object to get the updated word_timestamps
            db.refresh(text_obj)
            word_timestamps = text_obj.word_timestamps
            logger.info(f"Generated force alignment data with {len(word_timestamps) if word_timestamps else 0} word timestamps")
        else:
            logger.error(f"Failed to generate force alignment data for text {text_id}")
            return []

    if not word_timestamps:
        logger.error(f"No word timestamps available for text {text_id}")
        return []

    try:
        # Log the Claude API request
        logger.info("Anthropic API Request for sound effects analysis")
        
        # Create the force alignment JSON string to send to Claude
        force_alignment_json = json.dumps({
            "text_content": full_text,
            "word_timestamps": word_timestamps
        }, indent=2)
        
        # Replace placeholders like {{full_text}} with real values,
        # because the SDK does not support variables.
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0,
            system="you are a audio engineer and sound designer",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Identify ONLY short sound effects which are specific audio elements designed to highlight particular actions, objects, or moments. They're meant to draw attention and enhance specific events (footsteps, door slams, explosions, UI clicks).\n\nprovide:\n- A descriptive name (e.g., \"wooden-door-creak\", \"distant-thunder\")\n- The exact word where the effect should start\n- The exact word where the effect should end (can be same as start)\n- A detailed AudioX prompt for generating the sound\n- Rank the sound effects by their importance and contribution to the immersive audio experience (1 most important)\n- start_time and end_time - using the force alignment data in the json\n\nOutput ONLY!!! valid JSON in this format:\n{{\n  \"sound_effects\": [\n    {{\n      \"effect_name\": \"wooden-door-creak\",\n      \"description\": \"Old wooden door creaking open slowly\",\n      \"start_word\": \"door\",\n      \"end_word\": \"opened\",\n      \"prompt\": \"old wooden door creaking open slowly, horror movie style, high quality\",\n      \"rank\": \"2\",\n      \"start_time\": \"14.45\", \n      \"end_time\": \"16.0\"\n    }},\n    {{\n      \"effect_name\": \"thunder-distant\",\n      \"description\": \"Distant thunder rumbling\",\n      \"start_word\": \"thunder\",\n      \"end_word\": \"thunder\",\n      \"prompt\": \"distant thunder rumbling softly, cinematic, high quality\",\n      \"rank\": \"1\",\n      \"start_time\": \"18.32\", \n      \"end_time\": \"19.56\"\n    }}\n  ]\n}}\n\nText to analyze:\n{full_text}"
                        }
                    ]
                }
            ]
        )
        print(message.content)
        
        # Log the Claude API response
        logger.info("Anthropic API Response for sound effects analysis", extra={
            "anthropic_response": message.content[0].text
        })
        
        # Parse the JSON response
        response_text = message.content[0].text.strip()
        
        # Extract JSON from response (handle cases where Claude includes extra text)
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx != -1 and end_idx != -1:
            json_str = response_text[start_idx:end_idx]
            analysis_result = json.loads(json_str)
        else:
            raise ValueError("No valid JSON found in Claude response")
        
        sound_effects = analysis_result.get("sound_effects", [])
        logger.info(f"Claude identified {len(sound_effects)} potential sound effects for text {text_id}")
        
    except Exception as e:
        logger.error(f"Error calling Claude API for sound effects analysis: {e}")
        # Fallback to empty list rather than simulated data
        sound_effects = []
    
    processed_effects = []
    
    # Store the sound effects directly using timing data from Claude
    for effect in sound_effects:
        try:
            # Extract timing data from Claude's response
            start_time = float(effect.get('start_time', 0)) if effect.get('start_time') else None
            end_time = float(effect.get('end_time', 0)) if effect.get('end_time') else None
            
            # Extract rank from Claude's response
            rank = int(effect.get('rank', 0)) if effect.get('rank') else None
            
            # Calculate total_time based on the timing
            total_time = None
            if start_time is not None and end_time is not None:
                duration = end_time - start_time
                total_time = max(1, round(duration))  # Round to seconds, minimum 1 second
            
            crud.create_sound_effect(
                db=db,
                effect_name=effect['effect_name'],
                text_id=text_id,
                start_word=effect['start_word'],
                end_word=effect['end_word'],
                start_word_position=None,  # No longer using word positions
                end_word_position=None,    # No longer using word positions
                prompt=effect['prompt'],
                audio_data_b64="",  # Will be filled when audio is generated
                start_time=start_time,
                end_time=end_time,
                total_time=total_time,
                rank=rank
            )
            logger.info(f"Stored sound effect '{effect['effect_name']}' in database with timing: {start_time}s - {end_time}s")
            processed_effects.append(effect)
        except Exception as e:
            logger.error(f"Error storing sound effect '{effect['effect_name']}': {e}")
    
    return processed_effects

def generate_and_store_effect(db: Session, effect_id: int):
    """
    Generates audio for a sound effect and stores it.
    
    Args:
        db: Database session.
        effect_id: The ID of the sound effect to generate.
    """
    effect = crud.get_sound_effect(db, effect_id=effect_id)
    if not effect:
        logger.error(f"Cannot generate audio for non-existent effect_id {effect_id}")
        return

    logger.info(f"Starting audio generation for effect: {effect.effect_name} (ID: {effect_id})")

    # Use the pre-calculated total_time from the database
    duration = effect.total_time
    if duration is None or duration <= 0:
        logger.error(f"Invalid duration ({duration}) for effect {effect_id}. Aborting generation.")
        return

    # Generate audio using AudioX
    logger.info(f"Generating audio for '{effect.effect_name}' with prompt: '{effect.prompt}' and duration: {duration}s")
    
    try:
        # Get AudioX client
        client = get_audiox_client()
        if not client:
            logger.error("AudioX client not available, keeping audio_data_b64 empty")
            audio_b64 = ""
        else:
            # Call AudioX API
            logger.info(f"Calling AudioX API with parameters: prompt='{effect.prompt[:50]}...', duration={duration}, cfg_scale=8, steps=100")
            try:
                result = client.predict(
                    prompt=effect.prompt,
                    seconds_total=float(duration),
                    cfg_scale=8.0,
                    steps=100.0,
                    api_name="/generate_cond"
                )
                
                logger.info(f"AudioX API returned result type: {type(result)}, length: {len(result) if hasattr(result, '__len__') else 'N/A'}")
                
                # result[1] contains the audio file path
                audio_file_path = result[1]
                logger.info(f"Audio file path from AudioX: {audio_file_path}")
                
                # Convert audio file to base64
                audio_b64 = _convert_audio_to_base64(audio_file_path)
                
                # Clean up temporary file if it exists
                if os.path.exists(audio_file_path):
                    try:
                        os.remove(audio_file_path)
                        logger.debug(f"Cleaned up temporary audio file: {audio_file_path}")
                    except Exception as e:
                        logger.warning(f"Could not remove temporary file {audio_file_path}: {e}")
                
                logger.info(f"Successfully generated audio for effect '{effect.effect_name}'")
            except Exception as api_error:
                logger.error(f"AudioX API call failed: {api_error}")
                logger.error(f"API Error type: {type(api_error).__name__}")
                if hasattr(api_error, 'args') and api_error.args:
                    logger.error(f"API Error args: {api_error.args}")
                raise  # Re-raise to trigger fallback
    
    except Exception as e:
        logger.error(f"Failed to generate audio for effect {effect_id}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {str(e)}")
        # Keep audio_data_b64 empty instead of using placeholder
        audio_b64 = ""
        logger.info("Keeping audio_data_b64 empty due to generation failure")
    
    # Store the audio in the main sound_effects table (empty if generation failed)
    crud.update_sound_effect_audio(
        db, 
        effect_id=effect_id, 
        audio_data_b64=audio_b64,
        start_time=None, # To be updated in the final mixing step
        end_time=None
    )

    logger.info(f"Finished processing for effect {effect_id}")

def _convert_audio_to_base64(audio_file_path: str) -> str:
    """
    Convert an audio file to base64 encoded string.
    
    Args:
        audio_file_path: Path to the audio file
        
    Returns:
        Base64 encoded audio data
    """
    try:
        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            logger.debug(f"Converted audio file to base64, size: {len(audio_b64)} characters")
            return audio_b64
    except Exception as e:
        logger.error(f"Failed to convert audio file to base64: {e}")
        # Return a minimal valid WAV file as fallback
        return "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA" 