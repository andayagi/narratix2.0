from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import base64

from db.database import get_db
from db import crud, models
from services import speech_generation, background_music, combine_export_audio, force_alignment
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
    
    # Generate audio - now returns True/False instead of file paths
    success = speech_generation.generate_text_audio(db, text_id)
    
    # Return the generation status
    return {
        "text_id": text_id,
        "success": success,
    }

@router.post("/text/{text_id}/generate-segments", response_model=Dict[str, Any])
async def generate_segments_audio(
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
    
    # Generate audio - now returns True/False instead of file paths
    success = speech_generation.generate_text_audio(db, text_id)
    
    # Return the generation status
    return {
        "text_id": text_id,
        "success": success,
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

@router.post("/text/{text_id}/export", response_model=Dict[str, Any])
async def export_final_audio(
    text_id: int,
    db: Session = Depends(get_db)
):
    """Export final audio with background music for a text"""
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
    
    # Get segments to verify audio is generated
    segments = crud.get_segments_by_text(db, text_id)
    segments_with_audio = [segment for segment in segments if segment.audio_data_b64]
    
    if not segments_with_audio:
        raise HTTPException(status_code=400, detail="No segments have audio generated. Generate audio first.")
    
    # Export final audio
    audio_file = combine_export_audio.export_final_audio(db, text_id)
    
    if not audio_file:
        raise HTTPException(status_code=500, detail="Failed to export final audio")
    
    return {
        "text_id": text_id,
        "audio_file": audio_file
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
    
    # Check for audio data in the segments
    segments_with_audio = [segment for segment in segments if segment.audio_data_b64]
    
    if not segments_with_audio:
        return {
            "text_id": text_id,
            "status": "not_generated",
            "segments_count": 0,
            "segments_with_audio_count": 0
        }
    
    # Return audio info 
    return {
        "text_id": text_id,
        "status": "generated",
        "segments_count": len(segments),
        "segments_with_audio_count": len(segments_with_audio)
    }

@router.get("/text/{text_id}/segment/{segment_id}/audio")
async def get_segment_audio(
    text_id: int,
    segment_id: int,
    db: Session = Depends(get_db)
):
    """Get audio for a specific segment"""
    # Get the segment
    segment = db.query(models.TextSegment).filter(
        models.TextSegment.id == segment_id,
        models.TextSegment.text_id == text_id
    ).first()
    
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    if not segment.audio_data_b64:
        raise HTTPException(status_code=404, detail="Audio not generated for this segment")
    
    # Decode base64 audio data
    audio_bytes = base64.b64decode(segment.audio_data_b64)
    
    return Response(content=audio_bytes, media_type="audio/mpeg")

@router.get("/file/{filename}")
async def get_audio_file(
    filename: str
):
    """Get an audio file by filename"""
    # Check if the file exists in the output directory
    output_dir = os.path.join(os.getcwd(), "output")
    file_path = os.path.join(output_dir, filename)
    
    # If not found in output, check in background_music directory
    if not os.path.exists(file_path):
        bg_music_dir = os.path.join(settings.AUDIO_STORAGE_PATH, "background_music")
        file_path = os.path.join(bg_music_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Read and return the file
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
    
    return Response(content=audio_bytes, media_type="audio/mpeg")

@router.post("/text/{text_id}/force-align", response_model=Dict[str, Any])
async def run_force_alignment_for_text(
    text_id: int,
    db: Session = Depends(get_db)
):
    """
    Run force alignment on the speech-only audio for a text.
    This generates word-level timestamps.
    """
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")

    # Check if segments have audio data
    segments = crud.get_segments_by_text(db, text_id)
    if not any(s.audio_data_b64 for s in segments):
         raise HTTPException(status_code=400, detail="Speech has not been generated for this text's segments. Please generate audio first.")

    success = force_alignment.run_force_alignment(db, text_id)

    if not success:
        raise HTTPException(status_code=500, detail="Force alignment failed.")

    # Fetch the updated timestamps to return them
    updated_text = crud.get_text(db, text_id)
    
    return {
        "text_id": text_id,
        "success": True,
        "word_timestamps": updated_text.word_timestamps
    }