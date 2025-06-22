"""
Unified audio analysis service that combines sound effects and background music analysis.
This service replaces separate calls to Claude for each audio type with a single unified analysis.
"""
import json
import anthropic
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session

from utils.logging import get_logger
from utils.config import settings
from db import crud
# Removed force alignment dependency - using word placement instead
from utils.timing import time_it

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

logger = get_logger(__name__)

@time_it("unified_audio_analysis")
def analyze_text_for_audio(db: Session, text_id: int) -> Tuple[Optional[str], List[Dict]]:
    """
    Unified analysis that generates both soundscape and sound effects in a single Claude call.
    
    Args:
        db: Database session
        text_id: ID of the text to analyze
        
    Returns:
        Tuple of (soundscape_prompt, sound_effects_list)
    """
    # Get text content from database
    db_text = crud.get_text(db, text_id)
    if not db_text:
        logger.error(f"Text with ID {text_id} not found")
        return None, []
    
    full_text = db_text.content
    
    # Create word placement data (word with numerical position)
    words = full_text.split()
    word_placement = []
    for i, word in enumerate(words, 1):
        # Clean word of punctuation for matching purposes
        clean_word = word.strip('.,!?;:"()[]{}').lower()
        word_placement.append({
            "word": word,
            "placement": i,
            "clean_word": clean_word
        })
    
    logger.info(f"Created word placement data with {len(word_placement)} words for text {text_id}")
    
    # Create the word placement JSON string
    word_placement_json = json.dumps({
        "word_placement": word_placement
    }, indent=2)
    
    # Retry configuration for API overload handling
    max_retries = 3
    base_delay = 15  # Start with 15 seconds
    max_delay = 90   # Cap at 90 seconds
    
    message = None
    for attempt in range(max_retries + 1):
        try:
            # Log the Claude API request
            if attempt > 0:
                logger.info(f"Anthropic API Request for unified audio analysis (attempt {attempt + 1}/{max_retries + 1})")
            else:
                logger.info("Anthropic API Request for unified audio analysis")
            
            # Single call to Claude for both analyses
            message = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=3854,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"analyze according to the following:\n\nsoundscape: atmospheric sounds that will be played in the background of this entire text. Focus on concrete instructions like background noises (rain, wind, crowd cheering), tempo, instrumentation (if any), rhythm, and musical motifs. mention the genre of the book. 1-2 sentences.\n\nsound effects:\n- Name of sound (e.g., \"wooden-door-creak\", \"distant-thunder\")\n- The exact word where the effect should start\n- The exact word where the effect should end (can be same as start)\n- A detailed AudioX prompt for generating the sound\n- Rank the sound effects by their importance and contribution to the immersive audio experience (1 most important)\n- start_word_number and end_word_number (can be the same) - the numerical position of the word\n- Background music can NOT be sound effects\n\nOUTPUT FORMAT:\n{{\n  \"sound_effects\": [\n    {{\n      \"effect_name\": \"wooden-door-creak\",\n      \"description\": \"Old wooden door creaking open slowly\",\n      \"start_word\": \"door\",\n      \"end_word\": \"opened\",\n      \"prompt\": \"old wooden door creaking open slowly, horror movie style, high quality\",\n      \"rank\": \"2\",\n      \"start_word_number\": \"3\", \n      \"end_word_number\": \"4\"\n    }},\n    {{\n      \"effect_name\": \"thunder-distant\",\n      \"description\": \"Distant thunder rumbling\",\n      \"start_word\": \"thunder\",\n      \"end_word\": \"thunder\",\n      \"prompt\": \"distant thunder rumbling softly, cinematic, high quality\",\n      \"rank\": \"1\",\n      \"start_word_number\": \"23\", \n      \"end_word_number\": \"23\"\n    }}\n  ],\n  \"soundscape\": \"Slow, ominous percussion with deep tribal drums mimicking a primal heartbeat. Low, rumbling bass undertones create tension. Sparse, dissonant string elements suggest a dark fantasy or horror genre, with a rhythmic pattern that suggests impending danger and mysterious exploration.\"\n}}\n\n\nNEVER address a sound in both soundscape and sound effects, unless it's crucial for the storyline\n\nWord placement data (use this to find start_word_number and end_word_number):\n{word_placement_json}\n\nText:\n{full_text}"
                            }
                        ]
                    }
                ]
            )
            # If we get here, the request succeeded
            break
            
        except Exception as e:
            error_str = str(e)
            # Check if this is an overload error and we have retries left
            if ("overloaded" in error_str.lower() or "529" in error_str) and attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)  # Exponential backoff with cap
                logger.warning(f"API overloaded, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries + 1})")
                
                import time
                time.sleep(delay)
                continue
            else:
                # Re-raise the exception if it's not overload or we're out of retries
                logger.error(f"Error in unified audio analysis: {error_str}")
                return None, []
    
    if message is None:
        logger.error("Failed to get response from Claude API after all retries")
        return None, []
    
    try:
        
        # Log the Claude API response
        logger.info("Anthropic API Response for unified audio analysis", extra={
            "anthropic_response": message.content[0].text
        })
        
        # Parse the JSON response
        response_text = message.content[0].text.strip()
        
        # Extract JSON from response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx != -1 and end_idx != -1:
            json_str = response_text[start_idx:end_idx]
            analysis_result = json.loads(json_str)
        else:
            raise ValueError("No valid JSON found in Claude response")
        
        # Extract soundscape and sound effects
        soundscape = analysis_result.get("soundscape", "")
        sound_effects = analysis_result.get("sound_effects", [])
        
        logger.info(f"Claude analysis completed - Soundscape: {bool(soundscape)}, Sound effects: {len(sound_effects)}")
        
        # Process sound effects with word number data
        processed_effects = []
        for effect in sound_effects:
            # Extract word numbers from Claude's response
            start_word_number = effect.get('start_word_number')
            end_word_number = effect.get('end_word_number')
            
            # Convert to integers if they exist
            if start_word_number:
                try:
                    effect['start_word_number'] = int(start_word_number)
                except (ValueError, TypeError):
                    effect['start_word_number'] = None
            
            if end_word_number:
                try:
                    effect['end_word_number'] = int(end_word_number)
                except (ValueError, TypeError):
                    effect['end_word_number'] = None
            
            processed_effects.append(effect)
        
        return soundscape, processed_effects
        
    except Exception as e:
        logger.error(f"Error in unified audio analysis: {e}")
        return None, []

# Removed find_word_timing function - no longer needed with word placement approach

@time_it("process_audio_analysis")
def process_audio_analysis_for_text(db: Session, text_id: int) -> Tuple[bool, Optional[str], List[Dict]]:
    """
    Complete end-to-end audio analysis processing:
    1. Analyze text with unified Claude call for both soundscape and sound effects
    2. Store soundscape as background music prompt
    3. Store sound effects in database
    
    Args:
        db: Database session
        text_id: ID of the text to process
        
    Returns:
        Tuple of (success, soundscape_prompt, sound_effects_list)
    """
    # Delete existing sound effects and clear background music audio to avoid duplicates
    deleted_count = crud.delete_sound_effects_by_text(db, text_id)
    logger.info(f"Deleted {deleted_count} existing sound effects for text {text_id}")
    
    # Clear any existing background music audio data
    db_text = crud.get_text(db, text_id)
    if db_text and db_text.background_music_audio_b64:
        db_text.background_music_audio_b64 = None
        db.commit()
        logger.info(f"Cleared existing background music audio for text {text_id}")
    
    # Run unified analysis
    soundscape, sound_effects = analyze_text_for_audio(db, text_id)
    
    if not soundscape and not sound_effects:
        logger.error(f"Audio analysis failed for text {text_id}")
        return False, None, []
    
    # Store soundscape as background music prompt
    if soundscape:
        try:
            db_text = crud.get_text(db, text_id)
            if db_text:
                db_text.background_music_prompt = soundscape
                db.commit()
                logger.info(f"Stored soundscape as background music prompt for text {text_id}")
        except Exception as e:
            logger.error(f"Error storing soundscape: {e}")
    
    # Apply text length filtering for sound effects
    if sound_effects:
        text_length = len(crud.get_text(db, text_id).content)
        max_effects = max(1, text_length // 700)
        
        logger.info(f"Text length: {text_length} characters, allowing max {max_effects} sound effects")
        
        # Sort by rank and limit
        for effect in sound_effects:
            try:
                effect['rank'] = int(effect.get('rank', 999))
            except (ValueError, TypeError):
                effect['rank'] = 999
        
        sound_effects.sort(key=lambda x: x['rank'])
        sound_effects = sound_effects[:max_effects]
        
        # Store sound effects in database
        for effect in sound_effects:
            try:
                start_word_number = effect.get('start_word_number')
                end_word_number = effect.get('end_word_number')
                
                # Calculate a default duration based on word count (1 second per word)
                total_time = None
                if start_word_number is not None and end_word_number is not None:
                    word_count = end_word_number - start_word_number + 1
                    total_time = max(1, word_count)  # At least 1 second
                else:
                    total_time = 2  # Default 2 seconds for sound effects
                
                crud.create_sound_effect(
                    db=db,
                    effect_name=effect['effect_name'],
                    text_id=text_id,
                    start_word=effect['start_word'],
                    end_word=effect['end_word'],
                    start_word_position=start_word_number,
                    end_word_position=end_word_number,
                    prompt=effect['prompt'],
                    audio_data_b64="",
                    start_time=None,  # No timing data with word placement approach
                    end_time=None,    # No timing data with word placement approach
                    total_time=total_time,
                    rank=effect['rank']
                )
                logger.info(f"Stored sound effect '{effect['effect_name']}' for text {text_id} (words {start_word_number}-{end_word_number})")
            except Exception as e:
                logger.error(f"Error storing sound effect '{effect['effect_name']}': {e}")
    
    return True, soundscape, sound_effects 