from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Path, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from db.database import get_db
from db import crud
from services import audio_analysis
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/audio-analysis",
    tags=["Audio Analysis"],
    responses={404: {"description": "Not found"}},
)

@router.post("/{text_id}/analyze", status_code=202)
async def analyze_audio_for_text(
    text_id: int = Path(..., description="ID of the text to analyze"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Run unified audio analysis (soundscape + sound effects) for a text.
    
    This is a long-running background task that:
    1. Analyzes text with unified Claude call for both soundscape and sound effects
    2. Stores soundscape as background music prompt
    3. Stores sound effects in database
    
    Args:
        text_id: ID of the text to analyze
        
    Returns:
        Processing status and details
        
    Raises:
        404: Text not found
        500: Processing error
    """
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404, 
            detail=f"Text with ID {text_id} not found"
        )
    
    logger.info(f"Starting unified audio analysis for text ID {text_id}")
    
    # Run the complete analysis in the background
    background_tasks.add_task(audio_analysis.process_audio_analysis_for_text, db, text_id)
    
    return {
        "text_id": text_id,
        "status": "processing",
        "message": "Unified audio analysis initiated in background"
    }

@router.get("/{text_id}")
async def get_audio_analysis(
    text_id: int = Path(..., description="ID of the text to get analysis for"),
    db: Session = Depends(get_db)
):
    """
    Get complete audio analysis results for a text.
    
    Returns both soundscape and sound effects data.
    
    Args:
        text_id: ID of the text to get analysis for
        
    Returns:
        Complete audio analysis data
        
    Raises:
        404: Text not found or no analysis available
    """
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404, 
            detail=f"Text with ID {text_id} not found"
        )
    
    # Get soundscape (background music prompt)
    soundscape = db_text.background_music_prompt
    
    # Get sound effects
    sound_effects = crud.get_sound_effects_by_text(db, text_id)
    
    # Check if any analysis exists
    if not soundscape and not sound_effects:
        raise HTTPException(
            status_code=404,
            detail="No audio analysis found for this text"
        )
    
    logger.info(f"Retrieved audio analysis for text ID {text_id} - Soundscape: {bool(soundscape)}, Sound effects: {len(sound_effects)}")
    
    return {
        "text_id": text_id,
        "status": "completed",
        "data": {
            "soundscape": soundscape,
            "sound_effects": [
                {
                    "id": effect.effect_id,
                    "effect_name": effect.effect_name,
                    "start_word": effect.start_word,
                    "end_word": effect.end_word,
                    "start_word_position": effect.start_word_position,
                    "end_word_position": effect.end_word_position,
                    "prompt": effect.prompt,
                    "rank": effect.rank,
                    "total_time": effect.total_time,
                    "has_audio": bool(effect.audio_data_b64)
                }
                for effect in sound_effects
            ]
        }
    }

@router.get("/{text_id}/soundscape")
async def get_soundscape(
    text_id: int = Path(..., description="ID of the text to get soundscape for"),
    db: Session = Depends(get_db)
):
    """
    Get soundscape (background music prompt) for a text.
    
    Args:
        text_id: ID of the text to get soundscape for
        
    Returns:
        Soundscape data only
        
    Raises:
        404: Text not found or no soundscape available
    """
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404, 
            detail=f"Text with ID {text_id} not found"
        )
    
    # Get soundscape
    soundscape = db_text.background_music_prompt
    if not soundscape:
        raise HTTPException(
            status_code=404,
            detail="No soundscape found for this text"
        )
    
    logger.info(f"Retrieved soundscape for text ID {text_id}")
    
    return {
        "text_id": text_id,
        "status": "completed",
        "data": {
            "soundscape": soundscape
        }
    }

@router.get("/{text_id}/sound-effects")
async def get_sound_effects_from_analysis(
    text_id: int = Path(..., description="ID of the text to get sound effects for"),
    db: Session = Depends(get_db)
):
    """
    Get sound effects for a text.
    
    Args:
        text_id: ID of the text to get sound effects for
        
    Returns:
        Sound effects data only
        
    Raises:
        404: Text not found or no sound effects available
    """
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404, 
            detail=f"Text with ID {text_id} not found"
        )
    
    # Get sound effects
    sound_effects = crud.get_sound_effects_by_text(db, text_id)
    if not sound_effects:
        raise HTTPException(
            status_code=404,
            detail="No sound effects found for this text"
        )
    
    logger.info(f"Retrieved {len(sound_effects)} sound effects for text ID {text_id}")
    
    return {
        "text_id": text_id,
        "status": "completed",
        "data": {
            "sound_effects": [
                {
                    "id": effect.effect_id,
                    "effect_name": effect.effect_name,
                    "start_word": effect.start_word,
                    "end_word": effect.end_word,
                    "start_word_position": effect.start_word_position,
                    "end_word_position": effect.end_word_position,
                    "prompt": effect.prompt,
                    "rank": effect.rank,
                    "total_time": effect.total_time,
                    "has_audio": bool(effect.audio_data_b64)
                }
                for effect in sound_effects
            ]
        }
    } 