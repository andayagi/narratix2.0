from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os

from db.database import get_db
from db import crud, models
from services import audio_generation
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
    
    # Combine audio files
    combined_audio = audio_generation.combine_audio_files(audio_files)
    
    return {
        "text_id": text_id,
        "audio_file": combined_audio,
        "segments": audio_files
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