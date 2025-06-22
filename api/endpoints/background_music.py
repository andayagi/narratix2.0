from fastapi import APIRouter, Depends, HTTPException, Response, Path, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import base64
import os

from db.database import get_db
from db import crud
from services import background_music
from utils.config import settings
from utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/background-music",
    tags=["background-music"],
)

@router.post("/{text_id}/generate-prompt")
async def generate_music_prompt(
    text_id: int = Path(..., description="ID of the text to generate music prompt for"),
    db: Session = Depends(get_db)
):
    """
    Generate background music prompt for a given text.
    
    Args:
        text_id: ID of the text to generate music prompt for
        
    Returns:
        Generated music prompt and status
        
    Raises:
        404: Text not found
        500: Prompt generation error
    """
    logger.info(f"Starting music prompt generation for text ID {text_id}")
    
    # Check if text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404,
            detail=f"Text with ID {text_id} not found"
        )
    
    try:
        # Generate music prompt
        music_prompt = background_music.generate_background_music_prompt(db, text_id)
        
        if not music_prompt:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate music prompt"
            )
        
        logger.info(f"Successfully generated music prompt for text ID {text_id}")
        
        return {
            "text_id": text_id,
            "status": "success",
            "message": "Music prompt generated successfully",
            "data": {
                "music_prompt": music_prompt
            }
        }
        
    except Exception as e:
        logger.error(f"Error in music prompt generation for text ID {text_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Music prompt generation failed: {str(e)}"
        )

@router.post("/{text_id}/generate-audio")
async def generate_music_audio(
    text_id: int = Path(..., description="ID of the text to generate music audio for"),
    db: Session = Depends(get_db)
):
    """
    Generate background music audio for a given text (requires existing prompt).
    
    Args:
        text_id: ID of the text to generate music audio for
        
    Returns:
        Music generation status
        
    Raises:
        404: Text not found
        400: Music prompt not found
        500: Audio generation error
    """
    logger.info(f"Starting music audio generation for text ID {text_id}")
    
    # Check if text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404,
            detail=f"Text with ID {text_id} not found"
        )
    
    # Check if music prompt exists
    if not db_text.background_music_prompt:
        raise HTTPException(
            status_code=400,
            detail="Music prompt must be generated before audio generation"
        )
    
    try:
        # Generate music audio
        success = background_music.generate_background_music(db, text_id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate music audio"
            )
        
        logger.info(f"Successfully generated music audio for text ID {text_id}")
        
        return {
            "text_id": text_id,
            "status": "success",
            "message": "Music audio generated successfully",
            "data": {
                "music_prompt": db_text.background_music_prompt,
                "audio_generated": True
            }
        }
        
    except Exception as e:
        logger.error(f"Error in music audio generation for text ID {text_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Music audio generation failed: {str(e)}"
        )

@router.post("/{text_id}/process", status_code=202)
async def process_background_music(
    background_tasks: BackgroundTasks,
    text_id: int = Path(..., description="ID of the text to process"),
    force: bool = Query(False, description="Force reprocessing if already exists"),
    db: Session = Depends(get_db)
):
    """
    Run complete background music processing (prompt + audio generation).
    
    Args:
        text_id: ID of the text to process
        force: Force reprocessing if music already exists
        
    Returns:
        Processing status (background task initiated)
        
    Raises:
        404: Text not found
        400: Prerequisites not met
    """
    logger.info(f"Starting background music processing for text ID {text_id}")
    
    # Check if text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404,
            detail=f"Text with ID {text_id} not found"
        )
    
    # Check if music already exists and force flag
    if not force and db_text.background_music_audio_b64:
        return {
            "text_id": text_id,
            "status": "completed",
            "message": "Background music already exists. Use force=true to regenerate",
            "data": {
                "music_prompt": db_text.background_music_prompt,
                "audio_exists": True
            }
        }
    
    # Add background task for processing
    background_tasks.add_task(
        background_music.process_background_music_for_text,
        db, text_id
    )
    
    return {
        "text_id": text_id,
        "status": "processing",
        "message": "Background music processing initiated",
        "data": {
            "force_regenerate": force
        }
    }

@router.get("/{text_id}")
async def get_background_music_status(
    text_id: int = Path(..., description="ID of the text to get music status for"),
    db: Session = Depends(get_db)
):
    """
    Get background music status for a given text.
    
    Args:
        text_id: ID of the text to check status for
        
    Returns:
        Background music status and details
        
    Raises:
        404: Text not found
    """
    # Check if text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404,
            detail=f"Text with ID {text_id} not found"
        )
    
    # Check music status
    has_prompt = bool(db_text.background_music_prompt)
    has_audio = bool(db_text.background_music_audio_b64)
    
    # Determine status
    if has_audio:
        status = "completed"
        message = "Background music is fully generated"
    elif has_prompt:
        status = "prompt_only"
        message = "Music prompt exists but audio not generated"
    else:
        status = "not_generated"
        message = "No background music generated"
    
    return {
        "text_id": text_id,
        "status": status,
        "message": message,
        "data": {
            "has_prompt": has_prompt,
            "has_audio": has_audio,
            "music_prompt": db_text.background_music_prompt if has_prompt else None,
            "last_updated": db_text.last_updated.isoformat() if db_text.last_updated else None
        }
    }

@router.get("/{text_id}/audio")
async def download_background_music(
    text_id: int = Path(..., description="ID of the text to download music for"),
    format: str = Query("mp3", description="Audio format"),
    db: Session = Depends(get_db)
):
    """
    Download background music audio file for a given text.
    
    Args:
        text_id: ID of the text to download music for
        format: Audio format (currently only mp3 supported)
        
    Returns:
        Background music audio file
        
    Raises:
        404: Text not found or audio not generated
        400: Invalid format
    """
    # Validate format
    if format not in ["mp3"]:
        raise HTTPException(
            status_code=400,
            detail="Only mp3 format is currently supported"
        )
    
    # Check if text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404,
            detail=f"Text with ID {text_id} not found"
        )
    
    # Check if background music exists
    if not db_text.background_music_audio_b64:
        raise HTTPException(
            status_code=404,
            detail="Background music not generated for this text"
        )
    
    try:
        # Decode base64 audio
        audio_bytes = base64.b64decode(db_text.background_music_audio_b64)
        
        # Return as file download
        filename = f"background_music_text_{text_id}.{format}"
        
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error downloading background music for text ID {text_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download background music: {str(e)}"
        ) 