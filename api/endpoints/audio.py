from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os

from db.database import get_db
from db import crud, models
from services import audio_generation, background_music
from utils.config import settings

router = APIRouter(
    prefix="/api/audio",
    tags=["audio"],
)

@router.post("/text/{text_id}/generate", response_model=Dict[str, Any])
async def generate_audio_for_text(
    text_id: int,
    db: Session = Depends(get_db)
):
    """Generate audio for all segments of a text"""
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
    
    # Ensure text is analyzed
    if not db_text.analyzed:
        raise HTTPException(status_code=400, detail="Text must be analyzed before generating audio")
    
    # Generate audio
    audio_files = audio_generation.generate_text_audio(db, text_id)
    
    # Return the audio file path directly since Hume already returns combined audio
    return {
        "text_id": text_id,
        "audio_file": audio_files,
        "segments": [audio_files] if audio_files else []
    }

@router.post("/text/{text_id}/background-music", response_model=Dict[str, Any])
async def generate_background_music(
    text_id: int,
    db: Session = Depends(get_db)
):
    """Generate background music for a text"""
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
    
    # Process background music (both prompt and music generation)
    success, prompt, music_file = background_music.process_background_music_for_text(db, text_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to generate background music")
    
    return {
        "text_id": text_id,
        "prompt": prompt,
        "music_file": music_file
    }

@router.post("/text/{text_id}/mix-audio", response_model=Dict[str, Any])
async def mix_narration_with_background_music(
    text_id: int,
    bg_volume: float = 0.1,
    db: Session = Depends(get_db)
):
    """Mix narration audio with background music"""
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
    
    # Get narration audio file
    narration_audio = audio_generation.get_audio_for_text(db, text_id)
    if not narration_audio:
        raise HTTPException(status_code=400, detail="No narration audio found for this text")
    
    # Check if background music exists
    bg_music_dir = os.path.join(settings.AUDIO_STORAGE_PATH, "background_music")
    bg_music_file = os.path.join(bg_music_dir, f"bg_music_text_{text_id}.mp3")
    
    if not os.path.exists(bg_music_file):
        raise HTTPException(status_code=400, detail="No background music found for this text")
    
    # Mix the audio files
    mixed_audio = audio_generation.combine_audio_with_background(
        narration_audio=narration_audio, 
        background_music=bg_music_file,
        bg_volume=bg_volume
    )
    
    if not mixed_audio:
        raise HTTPException(status_code=500, detail="Failed to mix audio files")
    
    return {
        "text_id": text_id,
        "narration_audio": narration_audio,
        "background_music": bg_music_file,
        "mixed_audio": mixed_audio
    }

@router.get("/text/{text_id}/background-music", response_model=Dict[str, Any])
async def get_background_music_status(
    text_id: int,
    db: Session = Depends(get_db)
):
    """Get background music status for a text"""
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
    
    # Check if background music prompt exists
    if not db_text.background_music_prompt:
        return {
            "text_id": text_id,
            "status": "not_generated",
            "prompt": None,
            "music_file": None
        }
    
    # Check if background music file exists
    bg_music_dir = os.path.join(settings.AUDIO_STORAGE_PATH, "background_music")
    bg_music_file = os.path.join(bg_music_dir, f"bg_music_text_{text_id}.mp3")
    
    if os.path.exists(bg_music_file):
        return {
            "text_id": text_id,
            "status": "generated",
            "prompt": db_text.background_music_prompt,
            "music_file": bg_music_file
        }
    else:
        return {
            "text_id": text_id,
            "status": "prompt_only",
            "prompt": db_text.background_music_prompt,
            "music_file": None
        }

@router.get("/text/{text_id}", response_model=Dict[str, Any])
async def get_audio_for_text(
    text_id: int,
    db: Session = Depends(get_db)
):
    """Get audio information for a text"""
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
    
    # Get segments with audio
    segments = crud.get_segments_by_text(db, text_id)
    
    audio_files = [segment.audio_file for segment in segments if segment.audio_file]
    
    if not audio_files:
        return {
            "text_id": text_id,
            "status": "not_generated",
            "audio_file": None,
            "segments": []
        }
    
    # Return audio info
    return {
        "text_id": text_id,
        "status": "generated",
        "audio_file": audio_generation.combine_audio_files(audio_files),
        "segments": audio_files
    }

@router.get("/file/{file_name}")
async def get_audio_file(
    file_name: str
):
    """Get an audio file by name"""
    file_path = os.path.join(settings.AUDIO_STORAGE_PATH, file_name)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    with open(file_path, "rb") as f:
        content = f.read()
    
    return Response(content=content, media_type="audio/mpeg")