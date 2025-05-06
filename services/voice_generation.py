import requests
import json
import uuid
import time
from typing import Dict, Any
from sqlalchemy.orm import Session

from utils.config import settings
from utils.logging import get_logger
from db import crud, models

api_logger = get_logger("api.client", is_api=True)

# Hume AI base URL for voice creation
HUME_VOICE_API_URL = "https://api.hume.ai/v0/voice/creator"

def generate_character_voice(
    db: Session, 
    character_id: uuid.UUID, 
    character_name: str, 
    character_description: str
) -> str:
    """
    Generate a voice for a character using Hume AI
    
    Returns:
        provider_id: Hume AI voice ID
    """
    # Create a voice description based on character
    voice_description = f"Voice for character: {character_name}. {character_description}"
    
    # Prepare request for Hume AI
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": settings.HUME_API_KEY
    }
    
    payload = {
        "name": f"Narratix-{character_name}",
        "description": voice_description[:200],  # Limit description length
        "gender": "neutral",  # Default to neutral, can be improved with character analysis
        "use_case": "storytelling"
    }
    
    try:
        # Log API request
        api_logger.log_request(
            method="POST",
            url=HUME_VOICE_API_URL,
            headers=headers,
            body=payload
        )
        
        # Call Hume AI API to create voice
        response = requests.post(
            HUME_VOICE_API_URL,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        response_data = response.json()
        voice_id = response_data.get("voice_id")
        
        # Log successful response
        api_logger.log_response(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response_data
        )
        
        # Update character with voice ID
        crud.update_character_voice(db, character_id, voice_id)
        
        return voice_id
        
    except Exception as e:
        # Log error response if available
        if 'response' in locals():
            api_logger.log_response(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.text
            )
        
        api_logger.error(f"Character voice generation failed: {str(e)}", extra={
            "operation": "voice_generation",
            "character_id": str(character_id),
            "error": str(e),
            "status": "error"
        })
        raise

def ensure_character_voices(db: Session, text_id: uuid.UUID) -> Dict[uuid.UUID, str]:
    """
    Ensure all characters for a text have voices.
    Generate voices for characters that don't have one.
    
    Returns:
        Dict mapping character_id to provider_id
    """
    characters = crud.get_characters_by_text(db, text_id)
    voice_map = {}
    
    for character in characters:
        if not character.provider_id:
            # Generate voice if not already done
            voice_id = generate_character_voice(
                db, 
                character.id, 
                character.name, 
                character.description or ""
            )
            voice_map[character.id] = voice_id
        else:
            voice_map[character.id] = character.provider_id
    
    return voice_map