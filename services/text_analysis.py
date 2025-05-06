from anthropic import Anthropic
import json
from typing import Dict, List, Tuple, Any, TypedDict
from sqlalchemy.orm import Session
import uuid # Add UUID import

from utils.config import ANTHROPIC_API_KEY # Import ANTHROPIC_API_KEY directly
from utils.logging import get_logger # Import get_logger
from db import crud, models

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) # Use ANTHROPIC_API_KEY directly

# Initialize a logger for API interactions with API logging enabled
api_logger = get_logger("api.client", is_api=True)

# Define expected structures for clarity
class CharacterDetail(TypedDict):
    name: str
    is_narrator: bool
    speaking: bool
    persona_description: str
    intro_text: str # Renamed from 'text' in the example for clarity

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
        raise ValueError("Could not find JSON object in response")
        
    json_str = response_text[json_start:json_end]
    return json.loads(json_str)

def analyze_text_phase1_characters(text_content: str) -> List[CharacterDetail]:
    """Phase 1: Identify characters using Claude Haiku."""
    prompt = f"""<examples>
<example>
<text>
"Maya soared through the crimson sky on Azura's massive scaled back. 'We need to fly higher to avoid the storm clouds,' she called out, her voice determined yet concerned. 'Always so cautious,' laughed Kell from his perch on the nearby cliff. 'Your dragon can handle a little lightning!' His tone was teasing but affectionate. Maya frowned. 'I'm not risking Azura's wings again,' she replied firmly."
</text>
<ideal_output>
{{
  "characters": [
    {{
      "name": "Narrator",
      "is_narrator": true,
      "speaking":false,
      "persona_description": "Adult male, American accent, has the charismatic voice of a seasoned fantasy audiobook narrator, with a deep, resonant tone and a talent for dramatic pacing that brings every battle scene to life.",
      "text": "Welcome to this book, it's a fantasy romance taking place in a magical world of dragons and riders"
    }},
    {{
      "name": "Maya",
      "is_narrator": false,
      "speaking":true,
      "persona_description": "Adult female, American accent, has an intense, focused voice, like a weathered astronaut recounting a harrowing mission with controlled emotion and steely determination.",
      "text": "Hi, I'm Maya and this is my dragon Azura"
    }},
    {{
      "name": "Kell",
      "is_narrator": false,
      "speaking":true,
      "persona_description": "Adult male, American accent, has the charismatic, expressive voice of a mischievous extreme sports guru, who is both playful and warm",
       "text": "Hi, I'm Kell and I'm an experienced dragon rider"
    }}
  ]
}}
</ideal_output>
</example>
<example>
<text>
"I soared through the crimson sky on Azura's massive scaled back. 'We need to fly higher to avoid the storm clouds,' I called out, my voice determined yet concerned. 'Always so cautious,' laughed Kell from his perch on the nearby cliff. 'Your dragon can handle a little lightning!' His tone was teasing but affectionate. I frowned. 'I'm not risking Azura's wings again,' I replied firmly."
</text>
<ideal_output>
{{
  "characters": [
    {{
      "name": "protagonist",
      "is_narrator": true,
      "speaking":true,
      "persona_description": "Adult female, American accent, has an emotive voice, with a medium-high pitch that effortlessly conveys a wide range of feelings, making her an amazing voice for animation and heartfelt stories.",
       "text": "I'm a dragon rider and this is my dragon Azura"
    }},
    {{
      "name": "Kell",
      "is_narrator": false,
      "speaking":true,
      "persona_description": "Adult male, American accent, charismatic, expressive voice of a mischievous extreme sports guru, who speaks with a playful yet warm American accent, inspiring and thrilling listeners with every word",
       "text": "I'm Kell and I'm an experienced dragon rider"
    }}
  ]
}}
</ideal_output>
</example>
</examples>

Analyze text only for characters with dialogue parts and output only json file. 

Output Format:
Provide your analysis in the following JSON format:
{{
  "characters": [
    {{
      "name": "Character name or Narrator",
      "is_narrator": true/false,
      "speaking":true,
      "persona_description": "Age group, male OR female, short voice\\\\persona\\\\genre description",
      "text":"how the character would introduce itself to others in the book, if third person narrator then an introduction to the book"
    }},
    {{
      "name": "Another character",
      "is_narrator": false,
      "speaking":true,
      "persona_description": "Age group, male OR female, short voice\\\\persona\\\\genre description",
      "text":"how the character would introduce itself to others in the book"
    }}
  ]
}}


Instructions:
1. Identify all characters in the text
2. If the text uses third-person narration, add a "Narrator" record
3. IMPORTANT: For first-person narratives, do not create both a "protagonist" and a separate "Narrator" role - they are the same character.
4. For each character add if it speaks in the text speaking=true\\\\false
5. For each entry describe in one short sentence the voice for voiceover - [AGE GROUP] [MALE or FEMALE], American accent, [CORE VOCAL QUALITY + INTENSITY LEVEL] voice, [SPEAKING PATTERN], like [PRECISE CHARACTER ARCHETYPE] [PERFORMING CHARACTERISTIC ACTION WITH EMOTIONAL SUBTEXT]. words like young and youthful should be used only for children characters. 
6. For each entry describe how the character would introduce itself to others in the book, if third person narrator then an introduction to the book


Now analyze this text:
{text_content}
"""

    response = anthropic_client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=2000,
        temperature=1, 
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    
    response_content = response.content[0].text
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
    """Phase 2: Segment text and add voice instructions using Claude Sonnet."""
    
    # Prepare roles_names_json input for the second prompt
    roles_names = {"roles": [{"name": char["name"]} for char in characters]}
    roles_names_json = json.dumps(roles_names, indent=2)
    
    prompt = f"""<examples>
<example>
<text>
I soared through the crimson sky on Azura's massive scaled back. "We need to fly higher to avoid the storm clouds," I called out, my voice determined yet concerned. "Always so cautious," laughed Kell from his perch on the nearby cliff. "Your dragon can handle a little lightning!" His tone was teasing but affectionate. I frowned. "I'm not risking Azura's wings again," I replied firmly.
</text>
<roles_names_json>
{{
  "roles": [
    {{
      "name": "Protagonist"
    }},
    {{
      "name": "Kell"
    }}
  ]
}}
</roles_names_json>
<ideal_output>
{{
  "narrative_elements": [
    {{
      "role": "Protagonist",
      "text": "I soared through the crimson sky on Azura's massive scaled back.",
      "description": "Awe-struck, slightly breathless",
      "speed": 1.1,
      "trailing_silence": 0.3
    }},
    {{
      "role": "Protagonist",
      "text": "\\\"We need to fly higher to avoid the storm clouds,\\\"",
      "description": "Determined yet concerned, slightly raised voice",
      "speed": 1.2,
      "trailing_silence": 0.1
    }},
    {{
      "role": "Protagonist",
      "text": "I called out, my voice determined yet concerned.",
      "description": "Neutral, informative tone",
      "speed": 1.0,
      "trailing_silence": 0.2
    }},
    {{
      "role": "Kell",
      "text": "\\\"Always so cautious,\\\"",
      "description": "Teasing, affectionate laughter",
      "speed": 0.9,
      "trailing_silence": 0.1
    }},
    {{
      "role": "Protagonist",
      "text": "laughed Kell from his perch on the nearby cliff.",
      "description": "Neutral, informative tone",
      "speed": 1.0,
      "trailing_silence": 0.1
    }},
    {{
      "role": "Kell",
      "text": "\\\"Your dragon can handle a little lightning!\\\"",
      "description": "Confident, playful tone",
      "speed": 1.1,
      "trailing_silence": 0.2
    }},
    {{
      "role": "Protagonist",
      "text": "His tone was teasing but affectionate. I frowned.",
      "description": "Thoughtful, slightly conflicted",
      "speed": 0.9,
      "trailing_silence": 0.3
    }},
    {{
      "role": "Protagonist",
      "text": "\\\"I'm not risking Azura's wings again,\\\"",
      "description": "Firm, resolute tone",
      "speed": 1.0,
      "trailing_silence": 0.1
    }},
    {{
      "role": "Protagonist",
      "text": "I replied firmly.",
      "description": "Neutral, informative tone",
      "speed": 1.0,
      "trailing_silence": 0.5
    }}
  ]
}}
</ideal_output>
</example>
</examples>

breakdown the following text into segments wherever there's a dialog. for each segment, choose a name from the roles_names_json which character will voiceover it and provide additional voiceover instructions. 

Your goal is to create a JSON output that breaks down the text into segments, assigns roles to each segment, and provides acting instructions. Follow these steps:

1. Breakdown the text into segments wherever there's a dialog
2. Assign appropriate roles to each segment based on the provided roles_names_json.
3. For each segment add:
   - description: Provide concise acting instructions in natural language.
   - speed: Adjust the relative speaking rate on a non-linear scale from 0.25 (much slower) to 3.0 (much faster), where 1.0 represents normal speaking pace.
   - trailing_silence: Specify a duration of trailing silence (in seconds) to add after each utterance.

Best practices for providing acting instructions:
- Use precise emotions instead of broad terms (e.g., "melancholy" instead of "sad").
- Combine emotions with delivery styles (e.g., "excited but whispering").
- Indicate pacing using terms like "rushed", "measured", or "deliberate pause".
- Specify the audience when relevant (e.g., "speaking to a child").
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
      "trailing_silence": 0.5
    }},
    ...
  ]
}}

here's the roles_names_json and text:

<roles_names_json>
{roles_names_json}
</roles_names_json>

<text>
{text_content}
</text>
"""
    
    response = anthropic_client.messages.create(
        model="claude-3-7-sonnet-20250219", 
        max_tokens=4096,
        temperature=1, 
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    
    response_content = response.content[0].text
    analysis = _extract_json_from_response(response_content)
    
    return analysis.get("narrative_elements", [])

# This function now orchestrates the two calls
def get_analysis_results(text_id: str, content: str) -> Tuple[List[CharacterDetail], List[NarrativeElement]]:
    """
    Orchestrates the two-phase text analysis using Anthropic API calls.
    Returns detailed character info and narrative elements.
    """
    request_data_p1 = {"text_id": text_id, "content_length": len(content)}
    
    try:
        # Phase 1: Character Identification
        api_logger.log_request(
            method="POST",
            url="https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            body={"text": content, "phase": "character_identification"}
        )
        
        characters = analyze_text_phase1_characters(content)
        
        api_logger.log_response(
            status_code=200,
            body={"characters_count": len(characters)}
        )
        
    except Exception as e:
        api_logger.error(f"Error in text_analysis_phase1_characters: {e}", extra={
            "operation": "text_analysis_phase1_characters",
            "response_data": {"error": str(e)},
            "status": "error",
            "text_id": text_id
        })
        raise ValueError(f"Error in Phase 1 (Character Identification): {e}") from e
        
    if not characters:
         raise ValueError("Phase 1 did not return any characters.")

    # Phase 2: Segmentation
    request_data_p2 = {"text_id": text_id, "characters_count": len(characters)}
    
    try:
        api_logger.log_request(
            method="POST",
            url="https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            body={"text": content, "characters": characters, "phase": "segmentation"}
        )
        
        narrative_elements = analyze_text_phase2_segmentation(content, characters)
        
        api_logger.log_response(
            status_code=200,
            body={"segments_count": len(narrative_elements)}
        )
        
    except Exception as e:
        api_logger.error(f"Error in text_analysis_phase2_segmentation: {e}", extra={
            "operation": "text_analysis_phase2_segmentation",
            "response_data": {"error": str(e)},
            "status": "error",
            "text_id": text_id
        })
        raise ValueError(f"Error in Phase 2 (Segmentation): {e}") from e
        
    return characters, narrative_elements

def process_text_analysis(db: Session, text_id: str, content: str) -> models.Text:
    """
    Process text analysis using the two-phase approach and save results to database.
    """
    try:
        characters_data, narrative_elements = get_analysis_results(text_id, content)
    except Exception as e:
        # Log the failure at this higher level too if needed, or just re-raise
        print(f"Failed to get analysis results for text {text_id}: {e}") # Basic print log
        # Optionally update text status to failed analysis?
        raise

    # Get the Text object
    db_text = crud.get_text(db, uuid.UUID(text_id)) # Convert string ID to UUID
    if not db_text:
        raise ValueError(f"Text with ID {text_id} not found in database.")

    # Update text as analyzed
    db_text = crud.update_text_analyzed(db, db_text.id, analyzed=True)
    if not db_text:
        # This shouldn't happen if get_text succeeded, but defensive check
        raise ValueError(f"Failed to update text analysis status for ID {text_id}.")

    # Create characters in DB
    character_map = {}  # Map character names to DB Character objects
    db_characters = []
    for char_detail in characters_data:
        db_character = crud.create_character(
            db=db,
            text_id=db_text.id, # Use the UUID from db_text
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
            api_logger.warning(warning_message, extra={"context": {
                "operation": "segment_creation_warning",
                "details": f"Role '{character_name}' not found in character map.",
                "text_id": str(db_text.id)
            }})
    
    print(f"Processed text {text_id}: Created {len(db_characters)} characters and {len(db_segments)} segments.")
    
    return db_text 