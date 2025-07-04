from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db
from db import crud
from services import sound_effects as sfx_service
from schemas.sound_effect import SoundEffect, SoundEffectCreate

router = APIRouter(
    prefix="/api/sound-effects",
    tags=["Sound Effects"],
    responses={404: {"description": "Not found"}},
)

@router.get("/{text_id}", response_model=List[SoundEffect])
async def get_sound_effects_for_text(text_id: int, db: Session = Depends(get_db)):
    """Get all sound effects for a given text."""
    effects = crud.get_sound_effects_by_text(db, text_id=text_id)
    if not effects:
        raise HTTPException(status_code=404, detail="No sound effects found for this text")
    return effects

@router.post("/text/{text_id}/generate", status_code=202)
async def generate_sound_effects_for_text(text_id: int, background_tasks: BackgroundTasks, force: bool = Query(False, description="Force regeneration of existing sound effects"), db: Session = Depends(get_db)):
    """
    Generates audio for all sound effects of a text IN PARALLEL.
    This is a long-running background task.
    Requires that sound effects already exist in the database with prompts.
    
    Args:
        text_id: ID of the text to generate sound effects for
        force: Force regeneration of existing sound effects
    """
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
        
    # Get all sound effects for this text
    sound_effects = crud.get_sound_effects_by_text(db, text_id)
    if not sound_effects:
        raise HTTPException(status_code=404, detail="No sound effects found for this text. Run audio analysis first.")
    
    # Check if any effects need generation
    if force:
        # Clear existing audio data if force=true using proper CRUD function
        for effect in sound_effects:
            if effect.audio_data_b64:
                # Use the proper CRUD function that handles timestamps
                crud.update_sound_effect_audio(db, effect.effect_id, "")
        # No need for db.commit() as the CRUD function handles it
        effects_needing_generation = sound_effects
        message_suffix = " (forced regeneration)"
    else:
        effects_needing_generation = [effect for effect in sound_effects if not effect.audio_data_b64 or effect.audio_data_b64.strip() == ""]
        message_suffix = ""
    
    if effects_needing_generation:
        # Use parallel generation for all effects at once
        background_tasks.add_task(sfx_service.generate_sound_effects_for_text_parallel, text_id)
        return {"message": f"PARALLEL audio generation for {len(effects_needing_generation)} sound effects has been initiated in the background{message_suffix}."}
    else:
        return {"message": f"All {len(sound_effects)} sound effects already have generated audio."}

@router.post("/generate/{effect_id}", status_code=202)
async def generate_single_sound_effect(effect_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Generates audio for a single, specific sound effect.
    This is a long-running background task.
    """
    db_effect = crud.get_sound_effect(db, effect_id)
    if not db_effect:
        raise HTTPException(status_code=404, detail="Sound effect not found")

    if not db_effect.prompt:
        raise HTTPException(status_code=400, detail="Sound effect has no prompt. Run audio analysis first.")
    
    # Generate the sound effect audio
    background_tasks.add_task(sfx_service.generate_and_store_effect, effect_id)
    
    return {"message": f"Audio generation for effect {effect_id} has been initiated."}

@router.delete("/{effect_id}", status_code=200)
async def delete_sound_effect(effect_id: int, db: Session = Depends(get_db)):
    """Deletes a sound effect from the database."""
    success = crud.delete_sound_effect(db, effect_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sound effect not found")
    return {"message": "Sound effect deleted successfully."} 