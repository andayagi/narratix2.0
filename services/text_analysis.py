from anthropic import Anthropic
import json
import re
from typing import Dict, List, Tuple, Any, TypedDict
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from utils.config import settings
from utils.logging import get_logger
from db import crud, models
from datetime import datetime

# Initialize Anthropic client which will use our patched HTTP transport
anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# Initialize regular logger
logger = get_logger(__name__)

def _analyze_text_structure(text):
    """
    Analyzes a text and splits it into narrative and dialogue elements.
    Incorporated from process_text.py for better encapsulation.
    """
    # Split the text by dialogue markers (" or " or ").
    # The regex includes the markers in the split result.
    parts = re.split(r'(["""])', text)

    elements = []
    in_dialogue = False
    buffer = ""

    for part in parts:
        if part in ['"', '"', '"']:
            if in_dialogue:
                # End of dialogue
                if buffer.strip():
                    elements.append({"type": "dialogue", "content": buffer.strip().replace('\n', '  ')})
                buffer = ""
            else:
                # Start of dialogue
                if buffer.strip():
                    elements.append({"type": "narrative", "content": buffer.strip().replace('\n', '  ')})
                buffer = ""
            in_dialogue = not in_dialogue
        else:
            buffer += part

    if buffer.strip():
        # Add any remaining text as narrative
        elements.append({"type": "narrative", "content": buffer.strip().replace('\n', '  ')})
        
    # A simple approach to merge consecutive narrative parts
    merged_elements = []
    if elements:
        merged_elements.append(elements[0])
        for i in range(1, len(elements)):
            if elements[i]['type'] == 'narrative' and merged_elements[-1]['type'] == 'narrative':
                merged_elements[-1]['content'] += ' ' + elements[i]['content']
            else:
                merged_elements.append(elements[i])

    return {"elements": merged_elements}

# Define expected structures for clarity
class CharacterDetail(TypedDict):
    name: str
    is_narrator: bool
    speaking: bool
    persona_description: str
    intro_text: str 

class NarrativeElement(TypedDict):
    role: str
    text: str
    description: str
    speed: float
    trailing_silence: float


def _extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """Extracts JSON object from a string, handling potential markdown code blocks."""
    # Handle potential markdown ```json ... ``` blocks
    if response_text.strip().startswith("```json"):
        response_text = response_text.strip()[7:-3].strip()
    elif response_text.strip().startswith("```"):
         response_text = response_text.strip()[3:-3].strip()
         
    # Find the start and end of the outermost JSON object
    json_start = response_text.find('{')
    json_end = response_text.rfind('}') + 1
    
    if json_start == -1 or json_end == 0:
        logger.error(f"No JSON object found in response. Response: {response_text[:500]}...")
        raise ValueError("Could not find JSON object in response")
        
    json_str = response_text[json_start:json_end]
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Log the problematic JSON for debugging
        logger.error(f"JSON parsing failed: {e}")
        logger.error(f"JSON parse error at position {e.pos} (line {e.lineno}, column {e.colno})")
        logger.error(f"Problematic JSON (first 1000 chars): {json_str[:1000]}")
        logger.error(f"Response length: {len(response_text)} chars, JSON length: {len(json_str)} chars")
        
        # Check if this looks like a truncated response
        if "Expecting ',' delimiter" in str(e) or not json_str.rstrip().endswith('}'):
            raise ValueError(f"API response appears to be truncated. JSON parsing failed at position {e.pos}: {e}. Response length: {len(response_text)} chars")
        else:
            raise ValueError(f"Invalid JSON response: {e}")

def analyze_text_phase1_characters(text_content: str) -> List[CharacterDetail]:
    """Phase 1: Identify characters using Claude Haiku."""
    prompt = f"""your job is to put together a list of characters for voiceover, so only speaking characters and narrator (if exist).

Output only json:
{{
  "characters": [
    {{
      "name": "Character name or Narrator",
      "is_narrator": true/false,
      "speaking":true,
      "persona_description": "Age group, male OR female, short voice\\persona\\genre description",
      "text":"how the character would introduce itself to others in the book, if third person narrator then an introduction to the book"
    }},
    {{
      "name": "Another character",
      "is_narrator": false,
      "speaking":true,
      "persona_description": "Age group, male OR female, short voice\\persona\\genre description",
      "text":"how the character would introduce itself to others in the book"
    }}
  ]
}}


Instructions:
1. Identify ONLY characters that have dialogue parts (they are speaking in the story)
2. IMPORTANT: For FIRST-person narratives, do not create both a "protagonist" and a separate "Narrator" role - they are the same character. use only protagonist.
3. IMPORTANT: If none of the characters are the narrators - add "Narrator" entry
4. For each entry describe in one short sentence the voice for voiceover - [AGE GROUP (young adult\\adult\\elder)] [MALE OR FEMALE], American accent, [CORE VOCAL QUALITY + INTENSITY LEVEL] voice, [SPEAKING PATTERN], like [PRECISE CHARACTER ARCHETYPE] [PERFORMING CHARACTERISTIC ACTION WITH EMOTIONAL SUBTEXT]. words like young and youthful should be used only for children characters. don't use the word neutral.
5. For each entry describe how the character would introduce itself to others in the book, if third person narrator then an introduction to the book


Now analyze this text:
{text_content}"""

    # Define API parameters once to avoid duplication
    api_params = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 8192,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    # Log full Anthropics API request
    logger.info("Anthropic API Request", extra={"anthropic_request": api_params})
    
    response = anthropic_client.messages.create(**api_params)
    
    response_content = response.content[0].text
    # Log full Anthropics API response
    logger.info("Anthropic API Response", extra={"anthropic_response": response_content})
    analysis = _extract_json_from_response(response_content)
    
    # Map the API's 'text' field to our internal 'intro_text'
    characters_data = []
    for char_data in analysis.get("characters", []):
        characters_data.append({
            "name": char_data.get("name"),
            "is_narrator": char_data.get("is_narrator"),
            "speaking": char_data.get("speaking"),
            "persona_description": char_data.get("persona_description"),
            "intro_text": char_data.get("text") # Mapping
        })

    return characters_data

def analyze_text_phase2_segmentation(text_content: str, characters: List[CharacterDetail]) -> List[NarrativeElement]:
    """Phase 2: Segment text and add voice instructions using improved approach with internal text structure analysis."""
    
    # Step 1: Use internal text structure analysis to get structured elements
    structured_analysis = _analyze_text_structure(text_content)
    elements = structured_analysis.get("elements", [])
    
    # Prepare roles_names_json input for the second prompt
    roles_names = {"roles": [{"name": char["name"], "is_narrator": char["is_narrator"]} for char in characters]}
    roles_names_json = json.dumps(roles_names, indent=2)
    
    # Convert structured elements to JSON
    structured_elements_json = json.dumps(elements, indent=2)
    
    prompt = f"""enrich the following json elements.

1. Assign dialogues (quoted text) to the characters from the roles_names_json
2. other segments assigned to the character from the roles_names_json where is_narrator: true.
4. For each segment add:
   - description: Provide concise acting instructions in natural language.
   - speed: Adjust the relative speaking rate on a non-linear scale from 0.25 (much slower) to 3.0 (much faster), where 1.0 represents normal speaking pace.
   - trailing_silence: Specify a duration of trailing silence (in seconds) to add after each utterance, typical range 0.5 to 2 seconds.

Providing acting instructions:
- Use precise emotions instead of broad terms (e.g., "melancholy" instead of "sad").
- Combine emotions with delivery styles (e.g., "excited but whispering").
- Indicate pacing using terms like "rushed", "measured", or "deliberate pause".
- Performance context: narration, speaking to a crowd, intimate conversation, etc.
- Keep instructions concise (e.g., "sarcastic", "angry", "whispering").
- Use the speed parameter to adjust speech rate rather than describing it in the description field.

Your final output should be in the following JSON format:

{{
  "narrative_elements": [
    {{
      "role": "Character name or Narrator",
      "text": "Text for voiceover",
      "description": "Acting instructions",
      "speed": 1.0,
      "trailing_silence": 1.0
    }},
    ...
  ]
}}

here's the roles_names_json and structured elements:

roles_names_json:
{roles_names_json}

structured_elements:
{structured_elements_json}"""
    
    # Define API parameters once to avoid duplication
    api_params = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 16384,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    # Log full Anthropics API segmentation request
    logger.info("Anthropic API Segmentation Request", extra={"anthropic_request": api_params})
    
    response = anthropic_client.messages.create(**api_params)
    
    response_content = response.content[0].text
    # Log full Anthropics API segmentation response
    logger.info("Anthropic API Segmentation Response", extra={"anthropic_response": response_content})
    analysis = _extract_json_from_response(response_content)
    
    return analysis.get("narrative_elements", [])

# This function now orchestrates the two calls
def get_analysis_results(text_id: str, content: str) -> Tuple[List[CharacterDetail], List[NarrativeElement]]:
    """
    Orchestrates the two-phase text analysis using Anthropic API calls.
    Returns detailed character info and narrative elements.
    """
    # Add operation context to logger
    logger = get_logger(__name__, {"text_id": text_id, "operation": "text_analysis"})
    
    try:
        # Phase 1: Character Identification
        logger.info(f"Starting character identification for text {text_id} (length: {len(content)})")
        characters = analyze_text_phase1_characters(content)
        logger.info(f"Found {len(characters)} characters in text {text_id}")
        
    except Exception as e:
        logger.error(f"Error in text_analysis_phase1_characters: {e}", exc_info=True)
        raise ValueError(f"Error in Phase 1 (Character Identification): {e}") from e
        
    if not characters:
         raise ValueError("Phase 1 did not return any characters.")

    # Phase 2: Segmentation
    try:
        logger.info(f"Starting segmentation for text {text_id} with {len(characters)} characters")
        narrative_elements = analyze_text_phase2_segmentation(content, characters)
        logger.info(f"Created {len(narrative_elements)} narrative segments for text {text_id}")
        
    except Exception as e:
        logger.error(f"Error in text_analysis_phase2_segmentation: {e}", exc_info=True)
        raise ValueError(f"Error in Phase 2 (Segmentation): {e}") from e
        
    return characters, narrative_elements

def process_text_analysis(db: Session, text_id: int, content: str) -> models.Text:
    """
    Process text analysis using the two-phase approach and save results to database.
    """
    try:
        characters_data, narrative_elements = get_analysis_results(str(text_id), content)
    except Exception as e:
        # Log the failure at this higher level too if needed, or just re-raise
        print(f"Failed to get analysis results for text {text_id}: {e}") 
        raise

    # Get the text from database
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise ValueError(f"Text with ID {text_id} not found in database")
    
    db_text.analyzed = True
    db.commit()
    db.refresh(db_text)

    # Create characters in DB
    character_map = {}  # Map character names to DB Character objects
    db_characters = []
    for char_detail in characters_data:
        db_character = crud.create_character(
            db=db,
            text_id=db_text.id, 
            name=char_detail["name"],
            is_narrator=char_detail.get("is_narrator"),
            speaking=char_detail.get("speaking"),
            description=char_detail.get("persona_description"), 
            intro_text=char_detail.get("intro_text")
        )
        character_map[char_detail["name"]] = db_character
        db_characters.append(db_character)
    
    # Create segments in DB
    db_segments = []
    for i, element in enumerate(narrative_elements):
        character_name = element.get("role")
        db_character = character_map.get(character_name)
        
        if db_character:
            db_segment = crud.create_text_segment(
                db=db,
                text_id=db_text.id, 
                character_id=db_character.id, 
                text=element.get("text", ""), 
                sequence=i + 1, 
                description=element.get("description"),
                speed=element.get("speed"),
                trailing_silence=element.get("trailing_silence")
            )
            db_segments.append(db_segment)
        else:
            # Log or handle cases where a role in phase 2 doesn't match a character from phase 1
            warning_message = f"Role '{character_name}' found in segmentation but not in character list for text {text_id}. Skipping segment."
            print(f"Warning: {warning_message}")
            segment_logger = get_logger(__name__, {
                "operation": "segment_creation_warning",
                "details": f"Role '{character_name}' not found in character map.",
                "text_id": str(db_text.id)
            })
            segment_logger.warning(warning_message)
    
    print(f"Processed text {text_id}: Created {len(db_characters)} characters and {len(db_segments)} segments.")
    
    return db_text 