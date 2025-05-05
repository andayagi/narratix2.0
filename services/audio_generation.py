import os
import requests
import json
import uuid
import time
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from utils.config import settings
from utils.logging import APILogger
from db import crud, models

# Hume AI base URL for TTS
HUME_TTS_API_URL = "https://api.hume.ai/v0/tts/generate"

def generate_segment_audio(
    db: Session,
    segment_id: uuid.UUID,
    segment_content: str,
    voice_id: str
) -> str:
    """
    Generate audio for a text segment using Hume AI
    
    Returns:
        audio_file_path: Path to the generated audio file
    """
    # Create logging entry
    log_entry = APILogger.log_api_request(
        operation="segment_audio_generation",
        request_data={
            "segment_id": str(segment_id),
            "voice_id": voice_id,
            "content_length": len(segment_content)
        }
    )
    
    # Prepare request for Hume AI
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": settings.HUME_API_KEY
    }
    
    payload = {
        "text": segment_content,
        "voice_id": voice_id,
        "output_format": "mp3"
    }
    
    try:
        # Call Hume AI API for TTS
        response = requests.post(
            HUME_TTS_API_URL,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        # Save audio file
        file_name = f"{segment_id}.mp3"
        file_path = os.path.join(settings.AUDIO_STORAGE_PATH, file_name)
        
        with open(file_path, "wb") as f:
            f.write(response.content)
        
        # Log successful response
        APILogger.log_api_response(
            log_entry=log_entry,
            response_data={"file_path": file_path},
            status="success"
        )
        
        # Update segment with audio file path
        crud.update_segment_audio(db, segment_id, file_path)
        
        return file_path
        
    except Exception as e:
        # Log error
        APILogger.log_api_response(
            log_entry=log_entry,
            response_data={"error": str(e)},
            status="error"
        )
        raise

def generate_text_audio(db: Session, text_id: uuid.UUID) -> List[str]:
    """
    Generate audio for all segments of a text
    
    Returns:
        List of audio file paths
    """
    from .voice_generation import ensure_character_voices
    
    # Ensure all characters have voices
    voice_map = ensure_character_voices(db, text_id)
    
    # Get all segments
    segments = crud.get_segments_by_text(db, text_id)
    
    # Generate audio for each segment
    audio_files = []
    for segment in segments:
        if not segment.audio_file:
            voice_id = voice_map.get(segment.character_id)
            if voice_id:
                audio_file = generate_segment_audio(
                    db,
                    segment.id,
                    segment.content,
                    voice_id
                )
                audio_files.append(audio_file)
        else:
            audio_files.append(segment.audio_file)
    
    return audio_files

def combine_audio_files(audio_files: List[str]) -> str:
    """
    Combine multiple audio files into a single file
    
    Returns:
        Path to the combined audio file
    """
    # In a real implementation, use a library like pydub
    # For MVP, we'll implement a simple solution
    
    if not audio_files:
        return None
    
    if len(audio_files) == 1:
        return audio_files[0]
    
    # For MVP, just return the list of files
    # In a real implementation, we would combine them
    combined_file_name = f"combined_{uuid.uuid4()}.mp3"
    combined_file_path = os.path.join(settings.AUDIO_STORAGE_PATH, combined_file_name)
    
    # Log this operation for future improvement
    APILogger.log_api_request(
        operation="combine_audio",
        request_data={"files": audio_files},
    )
    
    # TODO: Implement actual audio combining
    # For now, just create a placeholder file with info
    with open(combined_file_path, "w") as f:
        f.write(f"Combined audio file with segments: {','.join(audio_files)}")
    
    return combined_file_path