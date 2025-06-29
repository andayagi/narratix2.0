"""
Webhook Recovery Service

Detects missing audio files and manually processes completed Replicate predictions
when webhooks fail to deliver.
"""

import replicate
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from db import crud
from db.database import SessionLocal
from services.replicate_audio import process_webhook_result
from utils.logging import get_logger

logger = get_logger(__name__)

def check_and_recover_missing_audio(text_id: int) -> Dict[str, Any]:
    """
    Check for missing audio files and attempt to recover them by manually
    processing completed Replicate predictions.
    
    Args:
        text_id: The text ID to check
        
    Returns:
        Recovery results summary
    """
    logger.info(f"Starting webhook recovery check for text {text_id}")
    
    db = SessionLocal()
    recovery_results = {
        "text_id": text_id,
        "background_music_recovered": False,
        "sound_effects_recovered": 0,
        "total_sound_effects": 0,
        "errors": []
    }
    
    try:
        # Check background music
        text = crud.get_text(db, text_id)
        if text and text.background_music_prompt and not text.background_music_audio_b64:
            logger.info(f"Background music missing for text {text_id}, attempting recovery...")
            bg_recovered = recover_background_music(text_id)
            recovery_results["background_music_recovered"] = bg_recovered
            if bg_recovered:
                logger.info(f"✅ Successfully recovered background music for text {text_id}")
            else:
                logger.warning(f"❌ Failed to recover background music for text {text_id}")
        
        # Check sound effects
        sound_effects = crud.get_sound_effects_by_text(db, text_id)
        recovery_results["total_sound_effects"] = len(sound_effects)
        
        for effect in sound_effects:
            if not effect.audio_data_b64:
                logger.info(f"Sound effect '{effect.effect_name}' (ID: {effect.id}) missing audio, attempting recovery...")
                sfx_recovered = recover_sound_effect(effect.id)
                if sfx_recovered:
                    recovery_results["sound_effects_recovered"] += 1
                    logger.info(f"✅ Successfully recovered sound effect '{effect.effect_name}'")
                else:
                    logger.warning(f"❌ Failed to recover sound effect '{effect.effect_name}'")
        
        return recovery_results
        
    except Exception as e:
        error_msg = f"Error during webhook recovery for text {text_id}: {str(e)}"
        logger.error(error_msg)
        recovery_results["errors"].append(error_msg)
        return recovery_results
    finally:
        db.close()

def recover_background_music(text_id: int) -> bool:
    """
    Attempt to recover background music by finding and processing the Replicate prediction.
    
    Args:
        text_id: The text ID
        
    Returns:
        True if recovery succeeded, False otherwise
    """
    try:
        # Get recent predictions that might match
        predictions = replicate.predictions.list()
        
        for prediction in predictions:
            # Check if this looks like a background music prediction for our text
            if (prediction.status == "succeeded" and 
                prediction.input and 
                "prompt" in prediction.input and
                prediction.output):
                
                # Try to process it as background music
                try:
                    mock_payload = {
                        "id": prediction.id,
                        "version": prediction.version,
                        "created_at": prediction.created_at.isoformat() if prediction.created_at else "",
                        "status": "succeeded",
                        "input": prediction.input,
                        "output": prediction.output
                    }
                    
                    success = process_webhook_result("background_music", text_id, mock_payload)
                    if success:
                        logger.info(f"Successfully recovered background music using prediction {prediction.id}")
                        return True
                        
                except Exception as e:
                    logger.debug(f"Failed to process prediction {prediction.id} as background music: {e}")
                    continue
        
        return False
        
    except Exception as e:
        logger.error(f"Error recovering background music for text {text_id}: {e}")
        return False

def recover_sound_effect(effect_id: int) -> bool:
    """
    Attempt to recover sound effect by finding and processing the Replicate prediction.
    
    Args:
        effect_id: The sound effect ID
        
    Returns:
        True if recovery succeeded, False otherwise
    """
    try:
        # Get recent predictions that might match
        predictions = replicate.predictions.list()
        
        for prediction in predictions:
            # Check if this looks like a sound effect prediction
            if (prediction.status == "succeeded" and 
                prediction.input and 
                "prompt" in prediction.input and
                prediction.output):
                
                # Try to process it as a sound effect
                try:
                    mock_payload = {
                        "id": prediction.id,
                        "version": prediction.version,
                        "created_at": prediction.created_at.isoformat() if prediction.created_at else "",
                        "status": "succeeded",
                        "input": prediction.input,
                        "output": prediction.output
                    }
                    
                    success = process_webhook_result("sound_effect", effect_id, mock_payload)
                    if success:
                        logger.info(f"Successfully recovered sound effect using prediction {prediction.id}")
                        return True
                        
                except Exception as e:
                    logger.debug(f"Failed to process prediction {prediction.id} as sound effect: {e}")
                    continue
        
        return False
        
    except Exception as e:
        logger.error(f"Error recovering sound effect {effect_id}: {e}")
        return False

def manual_webhook_recovery(text_id: int, prediction_ids: Dict[str, str]) -> Dict[str, bool]:
    """
    Manually recover webhooks using known prediction IDs.
    
    Args:
        text_id: The text ID
        prediction_ids: Dict with keys 'background_music' and 'sound_effect' mapping to prediction IDs
        
    Returns:
        Dict indicating success/failure for each type
    """
    results = {}
    
    # Recover background music
    if "background_music" in prediction_ids:
        try:
            prediction = replicate.predictions.get(prediction_ids["background_music"])
            if prediction.status == "succeeded" and prediction.output:
                mock_payload = {
                    "id": prediction.id,
                    "version": prediction.version,
                    "created_at": prediction.created_at.isoformat() if hasattr(prediction.created_at, 'isoformat') else str(prediction.created_at),
                    "status": "succeeded",
                    "input": prediction.input,
                    "output": prediction.output
                }
                
                success = process_webhook_result("background_music", text_id, mock_payload)
                results["background_music"] = success
                logger.info(f"Manual recovery of background music: {'✅ Success' if success else '❌ Failed'}")
            else:
                results["background_music"] = False
                logger.warning(f"Background music prediction {prediction_ids['background_music']} not ready")
        except Exception as e:
            results["background_music"] = False
            logger.error(f"Error recovering background music: {e}")
    
    # Recover sound effects
    if "sound_effect" in prediction_ids:
        try:
            prediction = replicate.predictions.get(prediction_ids["sound_effect"])
            if prediction.status == "succeeded" and prediction.output:
                # Get the first sound effect for this text
                db = SessionLocal()
                try:
                    sound_effects = crud.get_sound_effects_by_text(db, text_id)
                    if sound_effects:
                        effect_id = sound_effects[0].effect_id
                        
                        mock_payload = {
                            "id": prediction.id,
                            "version": prediction.version,
                            "created_at": prediction.created_at.isoformat() if prediction.created_at else "",
                            "status": "succeeded",
                            "input": prediction.input,
                            "output": prediction.output
                        }
                        
                        success = process_webhook_result("sound_effect", effect_id, mock_payload)
                        results["sound_effect"] = success
                        logger.info(f"Manual recovery of sound effect: {'✅ Success' if success else '❌ Failed'}")
                    else:
                        results["sound_effect"] = False
                        logger.warning(f"No sound effects found for text {text_id}")
                finally:
                    db.close()
            else:
                results["sound_effect"] = False
                logger.warning(f"Sound effect prediction {prediction_ids['sound_effect']} not ready")
        except Exception as e:
            results["sound_effect"] = False
            logger.error(f"Error recovering sound effect: {e}")
    
    return results 