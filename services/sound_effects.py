"""
Service for generating and managing sound effects from existing database prompts.

This service reads sound effect prompts that are already stored in the database
and generates audio for them using Replicate's webhook system.
Text analysis should be handled separately by the audio_analysis service.
"""
import os
import json
import subprocess
import tempfile
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from utils.logging import get_logger
from utils.config import settings
from utils.http_client import get_sync_client
from db import crud
from db.session_manager import managed_db_session
from utils.timing import time_it
from services.clients import ClientFactory

logger = get_logger(__name__)

def delete_existing_sound_effects(text_id: int) -> int:
    """
    Delete all existing sound effects for a given text_id.
    
    Args:
        text_id: The ID of the text to clean up.
        
    Returns:
        Number of deleted sound effects.
    """
    with managed_db_session() as db:
        deleted_count = crud.delete_sound_effects_by_text(db, text_id)
    logger.info(f"Deleted {deleted_count} existing sound effects for text {text_id}")
    return deleted_count

@time_it("generate_and_store_sound_effect")
def generate_and_store_effect(effect_id: int) -> bool:
    """
    Generate audio for a sound effect using Replicate webhook.
    Requires that the sound effect already exists in the database with a prompt.
    
    Args:
        effect_id: The ID of the sound effect to generate.
        
    Returns:
        True if webhook was successfully triggered, False otherwise.
    """
    from services.replicate_audio import create_webhook_prediction, ReplicateAudioConfig
    
    try:
        with managed_db_session() as db:
            # Get the sound effect from database
            effect = crud.get_sound_effect(db, effect_id=effect_id)
            if not effect:
                logger.error(f"Sound effect with ID {effect_id} not found")
                return False
            
            if not effect.prompt:
                logger.error(f"Sound effect {effect_id} has no prompt. Audio analysis must be run first.")
                return False

            # Use the pre-calculated total_time from the database
            duration = effect.total_time
            if duration is None or duration <= 0:
                logger.error(f"Invalid duration ({duration}) for effect {effect_id}. Setting default duration of 2 seconds.")
                duration = 2
            
            # Extract all needed data while session is active
            effect_name = effect.effect_name
            prompt = effect.prompt
            text_id = effect.text_id

        logger.info(f"Generating audio for sound effect '{effect_name}' with prompt: '{prompt}' and duration: {duration}s")
        
        # Create configuration for sound effect generation
        model_version = "stackadoc/stable-audio-open-1.0:9aff84a639f96d0f7e6081cdea002d15133d0043727f849c40abdd166b7c75a8"
        config = ReplicateAudioConfig(
            version=model_version,
            input={
                "prompt": prompt,
                "seconds_total": float(duration),
                "cfg_scale": 6.0,
                "steps": 100
            }
        )
        
        # Clear existing audio data to ensure we wait for new prediction
        with managed_db_session() as db:
            effect = crud.get_sound_effect(db, effect_id)
            if effect and effect.audio_data_b64:
                crud.update_sound_effect_audio(db, effect_id, None)
                logger.info(f"Cleared existing audio data for sound effect {effect_id} to wait for new prediction")
        
        # Trigger webhook-based generation
        prediction_id = create_webhook_prediction("sound_effect", effect_id, config)
        if prediction_id:
            logger.info(f"Sound effect generation webhook triggered for effect {effect_id}, prediction ID: {prediction_id}")
            with managed_db_session() as db:
                crud.create_log(
                    db=db,
                    text_id=text_id,
                    operation="sound_effect_generation_webhook_trigger",
                    status="success",
                    response={"effect_id": effect_id, "prediction_id": prediction_id, "message": "Webhook triggered successfully"}
                )
            return True
        else:
            logger.error(f"Failed to trigger sound effect generation webhook for effect {effect_id}")
            with managed_db_session() as db:
                crud.create_log(
                    db=db,
                    text_id=text_id,
                    operation="sound_effect_generation_webhook_trigger",
                    status="error",
                    response={"effect_id": effect_id, "error": "Failed to trigger webhook"}
                )
            return False
        
    except Exception as e:
        logger.error(f"Error triggering sound effect generation webhook for effect {effect_id}: {e}")
        # Try to get text_id for logging
        try:
            with managed_db_session() as db:
                effect = crud.get_sound_effect(db, effect_id=effect_id)
                if effect:
                    crud.create_log(
                        db=db,
                        text_id=effect.text_id,
                        operation="sound_effect_generation_webhook_trigger",
                        status="error",
                        response={"effect_id": effect_id, "error": str(e)}
                    )
        except Exception as log_error:
            logger.debug(f"Could not log error for effect {effect_id}: {log_error}")
        return False

@time_it("generate_sound_effects_for_text")
async def generate_sound_effects_for_text(text_id: int) -> bool:
    """
    Generate audio for all sound effects of a given text.
    Requires that sound effects already exist in the database with prompts.
    
    Args:
        text_id: The ID of the text to process.
        
    Returns:
        True if all webhooks were successfully triggered, False otherwise.
    """
    try:
        with managed_db_session() as db:
            # Get all sound effects for the given text
            effects = crud.get_sound_effects_by_text(db, text_id)
            
            if not effects:
                logger.info(f"No sound effects found for text {text_id}. Audio analysis must be run first.")
                return False
            
            logger.info(f"Starting audio generation for {len(effects)} sound effects of text {text_id}")
        
        success_count = 0
        # Generate audio for each effect
        for effect in effects:
            if generate_and_store_effect(effect.effect_id):
                success_count += 1
        
        all_webhooks_triggered = success_count == len(effects)
        
        if not all_webhooks_triggered:
            logger.error(f"Not all webhooks were triggered: {success_count}/{len(effects)} successful")
            return False
        
        logger.info(f"All {len(effects)} webhooks triggered successfully. Waiting for completion...")
        
        # Import and wait for all sound effects to complete
        from services.replicate_audio import wait_for_sound_effects_completion_event
        completed_count = await wait_for_sound_effects_completion_event(text_id)
        
        success = completed_count == len(effects)
        if success:
            logger.info(f"✅ All {len(effects)} sound effects completed successfully for text {text_id}")
        else:
            logger.error(f"❌ Only {completed_count}/{len(effects)} sound effects completed successfully for text {text_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error generating sound effects for text {text_id}: {e}")
        return False

@time_it("generate_sound_effects_for_text_parallel")
async def generate_sound_effects_for_text_parallel(text_id: int) -> bool:
    """
    Generate audio for all sound effects in parallel using threading.
    Requires that sound effects already exist in the database with prompts.
    
    Args:
        text_id: The ID of the text to process.
        
    Returns:
        True if all webhooks were successfully triggered, False otherwise.
    """
    import concurrent.futures
    
    try:
        with managed_db_session() as db:
            # Get all sound effects for the given text
            effects = crud.get_sound_effects_by_text(db, text_id)
            
            if not effects:
                logger.info(f"No sound effects found for text {text_id}. Audio analysis must be run first.")
                return False
            
            logger.info(f"Starting PARALLEL audio generation for {len(effects)} sound effects of text {text_id}")
            
            # Extract effect IDs and names while session is active (to avoid detached session issues)
            effect_data = [(effect.effect_id, effect.effect_name) for effect in effects]
            logger.info(f"Effect data extracted: {effect_data}")
        
        def generate_single_effect(effect_id: int) -> bool:
            """Worker function to generate a single effect"""
            return generate_and_store_effect(effect_id)
        
        # Use ThreadPoolExecutor for parallel Replicate API calls
        max_workers = min(len(effects), 3)  # Limit to 3 concurrent Replicate calls
        logger.info(f"Using {max_workers} parallel workers for {len(effects)} sound effects")
        
        success_count = 0
        failed_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all sound effect generation tasks using only effect_id
            future_to_effect_data = {
                executor.submit(generate_single_effect, effect_id): (effect_id, effect_name)
                for effect_id, effect_name in effect_data
            }
            
            # Wait for all to complete and log results
            for future in concurrent.futures.as_completed(future_to_effect_data):
                effect_id, effect_name = future_to_effect_data[future]
                try:
                    if future.result():  # This will raise any exception that occurred
                        success_count += 1
                        logger.info(f"✅ Completed sound effect '{effect_name}' ({success_count}/{len(effects)})")
                    else:
                        failed_count += 1
                        logger.error(f"❌ Failed sound effect '{effect_name}' (webhook not triggered)")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Failed sound effect '{effect_name}': {e}")
        
        all_webhooks_triggered = success_count == len(effects)
        
        if not all_webhooks_triggered:
            logger.error(f"Not all webhooks were triggered: {success_count}/{len(effects)} successful")
            return False
        
        logger.info(f"All {len(effects)} webhooks triggered successfully. Waiting for completion...")
        
        # Import and wait for all sound effects to complete
        from services.replicate_audio import wait_for_sound_effects_completion_event
        completed_count = await wait_for_sound_effects_completion_event(text_id)
        
        success = completed_count == len(effects)
        if success:
            logger.info(f"✅ All {len(effects)} sound effects completed successfully for text {text_id}")
        else:
            logger.error(f"❌ Only {completed_count}/{len(effects)} sound effects completed successfully for text {text_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in parallel sound effect generation for text {text_id}: {e}")
        return False

