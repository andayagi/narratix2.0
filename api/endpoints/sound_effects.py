from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db
from db import crud
from services import sound_effects as sfx_service
from services import speech_generation as speech_service
from schemas.sound_effect import SoundEffect, SoundEffectCreate

router = APIRouter(
    prefix="/api/sound-effects",
    tags=["Sound Effects"],
    responses={404: {"description": "Not found"}},
)

@router.post("/analyze/{text_id}", status_code=202)
async def analyze_sound_effects(text_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Analyzes a text for sound effect opportunities and stores them in the database.
    This is a long-running background task.
    """
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
        
    # First, generate audio and get word timestamps if not already present
    # This is a prerequisite for sound effect analysis
    # For now, we assume this has been done. A more robust implementation would check
    # and trigger this process if needed.
    
    # We need a combined audio to get timestamps, let's trigger the generation and alignment
    alignment_result = speech_service.generate_text_audio_with_alignment(db, text_id)
    
    if not alignment_result["alignment_success"]:
        raise HTTPException(status_code=500, detail="Force alignment failed, cannot analyze for sound effects.")

    word_timestamps = alignment_result["word_timestamps"]
    
    # Run the analysis in the background
    background_tasks.add_task(sfx_service.analyze_text_for_sound_effects, db, text_id, word_timestamps)
    
    return {"message": "Sound effect analysis has been initiated in the background."}

@router.get("/{text_id}", response_model=List[SoundEffect])
async def get_sound_effects_for_text(text_id: int, db: Session = Depends(get_db)):
    """Get all sound effects for a given text."""
    effects = crud.get_sound_effects_by_text(db, text_id=text_id)
    if not effects:
        raise HTTPException(status_code=404, detail="No sound effects found for this text")
    return effects

@router.post("/generate/{effect_id}", status_code=202)
async def generate_single_sound_effect(effect_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Generates audio for a single, specific sound effect.
    This is a long-running background task.
    """
    db_effect = crud.get_sound_effect(db, effect_id)
    if not db_effect:
        raise HTTPException(status_code=404, detail="Sound effect not found")

    # Get word timestamps for the text to calculate effect duration
    text_obj = crud.get_text(db, db_effect.text_id)
    if not text_obj or not text_obj.word_timestamps:
        raise HTTPException(status_code=400, detail="Text word timestamps not available. Run force alignment first.")

    # Generate the sound effect audio
    background_tasks.add_task(sfx_service.generate_and_store_effect, db, effect_id, text_obj.word_timestamps)
    
    return {"message": f"Audio generation for effect {effect_id} has been initiated."}

@router.delete("/{effect_id}", status_code=200)
async def delete_sound_effect(effect_id: int, db: Session = Depends(get_db)):
    """Deletes a sound effect from the database."""
    success = crud.delete_sound_effect(db, effect_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sound effect not found")
    return {"message": "Sound effect deleted successfully."} 