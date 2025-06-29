#!/usr/bin/env python3
"""
Standalone Sound Effects Audio Generation Script

This script generates audio for existing sound effect records using Replicate webhooks.

Usage:
    python sound_effects.py --text-id 123
    python sound_effects.py --text-id 123 --parallel           # Use parallel processing
    python sound_effects.py --text-id 123 --auto-start-server  # Auto-start server if needed
    python sound_effects.py --text-id 123 --skip-server-check  # Skip server health check
    python sound_effects.py --text-id 123 --sync               # Use synchronous processing (wait for results)

The script will:
1. Check if FastAPI server is running (can auto-start if not)
2. Clear existing audio data from sound effect records in the database
3. Generate new audio using Replicate webhooks from existing prompts
4. Save results to the database asynchronously via webhooks

Note: This script requires existing sound effect records with prompts in the database.
Use the text analysis service first if no sound effects exist.
"""

import sys
import os
import argparse
import requests
import time
import base64
from pathlib import Path
import replicate
from typing import List

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db import crud
from services.sound_effects import (
    generate_and_store_all_effects,
    generate_and_store_all_effects_parallel
)
from services.replicate_audio import ReplicateAudioConfig, AudioPostProcessor, SoundEffectProcessor
from utils.logging import get_logger
from utils.config import settings
from utils.http_client import get_sync_client

logger = get_logger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Standalone Sound Effects Audio Generation Service")
    
    parser.add_argument("--text-id", type=int, required=True, 
                       help="ID of text to generate sound effects audio for")
    parser.add_argument("--parallel", action="store_true",
                       help="Use parallel processing for faster generation")
    parser.add_argument("--skip-server-check", action="store_true",
                       help="Skip server health check and proceed anyway")
    parser.add_argument("--sync", action="store_true",
                       help="Use synchronous processing - wait for results and save directly to DB")
    
    return parser.parse_args()

def validate_sound_effects_exist(db, text_id: int) -> bool:
    """Validate that sound effect records with prompts exist for the text_id."""
    existing_effects = crud.get_sound_effects_by_text(db, text_id)
    
    if not existing_effects:
        logger.error(f"No sound effect records found for text_id {text_id}. Run text analysis first.")
        return False
    
    # Check if effects have prompts
    effects_with_prompts = [e for e in existing_effects if e.prompt and e.prompt.strip()]
    if not effects_with_prompts:
        logger.error(f"Found {len(existing_effects)} sound effects for text_id {text_id} but none have prompts. Run text analysis first.")
        return False
    
    logger.info(f"Found {len(effects_with_prompts)} sound effects with prompts for text_id {text_id}")
    return True

def check_server_health() -> bool:
    """Check if the FastAPI server is running and can receive webhooks."""
    try:
        # Try to reach the health endpoint or root endpoint
        health_url = f"{settings.BASE_URL}/docs"  # FastAPI docs endpoint should be available
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            logger.info(f"Server is running at {settings.BASE_URL}")
            return True
        else:
            logger.error(f"Server responded with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to server at {settings.BASE_URL}")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"Server at {settings.BASE_URL} is not responding (timeout)")
        return False
    except Exception as e:
        logger.error(f"Error checking server health: {e}")
        return False

def clear_audio_data(db, text_id: int):
    """Clear only the audio data from existing sound effect records."""
    logger.info(f"Clearing audio data from sound effects for text_id {text_id}")
    
    existing_effects = crud.get_sound_effects_by_text(db, text_id)
    
    for effect in existing_effects:
        crud.update_sound_effect_audio(db, effect.effect_id, "")
    
    logger.info(f"Cleared audio data from {len(existing_effects)} sound effect records")

def create_synchronous_prediction(config: ReplicateAudioConfig) -> dict:
    """
    Create a Replicate prediction and wait for completion synchronously.
    
    Args:
        config: ReplicateAudioConfig with generation parameters
        
    Returns:
        Prediction result dict with output
    """
    try:
        logger.info(f"Creating synchronous prediction with config: {config}")
        
        # Create prediction without webhook
        prediction = replicate.predictions.create(
            version=config.version.split(':')[-1] if ':' in config.version else config.version,
            input=config.input
        )
        
        logger.info(f"Created prediction {prediction.id}, waiting for completion...")
        
        # Poll for completion
        max_wait_time = 300  # 5 minutes max
        poll_interval = 5  # 5 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Refresh prediction status
            prediction = replicate.predictions.get(prediction.id)
            
            if prediction.status == "succeeded":
                logger.info(f"Prediction {prediction.id} completed successfully")
                return {
                    "id": prediction.id,
                    "status": prediction.status,
                    "output": prediction.output
                }
            elif prediction.status == "failed":
                logger.error(f"Prediction {prediction.id} failed: {prediction.error}")
                return {
                    "id": prediction.id,
                    "status": prediction.status,
                    "error": prediction.error
                }
            elif prediction.status in ["starting", "processing"]:
                logger.info(f"Prediction {prediction.id} status: {prediction.status}, waiting...")
                time.sleep(poll_interval)
            else:
                logger.warning(f"Prediction {prediction.id} has unexpected status: {prediction.status}")
                time.sleep(poll_interval)
        
        # Timeout
        logger.error(f"Prediction {prediction.id} timed out after {max_wait_time} seconds")
        return {
            "id": prediction.id,
            "status": "timeout",
            "error": f"Prediction timed out after {max_wait_time} seconds"
        }
        
    except Exception as e:
        logger.error(f"Error creating synchronous prediction: {e}")
        raise

def generate_and_store_effect_sync(db, effect_id: int) -> bool:
    """
    Generate and store a sound effect synchronously.
    
    Args:
        db: Database session
        effect_id: The ID of the sound effect to generate
        
    Returns:
        True if successful, False otherwise
    """
    effect = crud.get_sound_effect(db, effect_id=effect_id)
    if not effect:
        logger.error(f"Cannot generate audio for non-existent effect_id {effect_id}")
        return False

    logger.info(f"Starting synchronous audio generation for effect: {effect.effect_name} (ID: {effect_id})")

    # Use the pre-calculated total_time from the database
    duration = effect.total_time
    if duration is None or duration <= 0:
        logger.error(f"Invalid duration ({duration}) for effect {effect_id}. Aborting generation.")
        return False

    logger.info(f"Generating '{effect.effect_name}' with prompt: '{effect.prompt}' and duration: {duration}s")
    
    try:
        # Create configuration for sound effect generation
        model_version = "stackadoc/stable-audio-open-1.0:9aff84a639f96d0f7e6081cdea002d15133d0043727f849c40abdd166b7c75a8"
        config = ReplicateAudioConfig(
            version=model_version,
            input={
                "prompt": effect.prompt,
                "seconds_total": float(duration),
                "cfg_scale": 6.0,
                "steps": 100
            },
            duration=duration
        )
        
        # Generate synchronously
        prediction_result = create_synchronous_prediction(config)
        
        if prediction_result["status"] != "succeeded":
            logger.error(f"Prediction failed for effect {effect_id}: {prediction_result.get('error', 'Unknown error')}")
            return False
        
        # Process the result using the same processor as webhooks
        processor = SoundEffectProcessor()
        success = processor.process_and_store(effect_id, prediction_result)
        
        if success:
            logger.info(f"Successfully generated and stored audio for effect {effect_id}")
        else:
            logger.error(f"Failed to process and store audio for effect {effect_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to generate audio for effect {effect_id}: {e}")
        return False

def start_parallel_webhook_predictions(db, text_id: int) -> List[str]:
    """
    Start all sound effect predictions in parallel using webhooks.
    
    Args:
        db: Database session
        text_id: The ID of the text
        
    Returns:
        List of prediction IDs that were started
    """
    from services.replicate_audio import create_webhook_prediction
    
    effects = crud.get_sound_effects_by_text(db, text_id)
    
    if not effects:
        logger.info(f"No sound effects found for text {text_id}")
        return []
    
    logger.info(f"Starting parallel webhook predictions for {len(effects)} sound effects")
    
    prediction_ids = []
    
    for effect in effects:
        try:
            # Use the pre-calculated total_time from the database
            duration = effect.total_time
            if duration is None or duration <= 0:
                logger.error(f"Invalid duration ({duration}) for effect {effect.effect_id}. Skipping.")
                continue

            logger.info(f"Starting prediction for '{effect.effect_name}' (ID: {effect.effect_id})")
            
            # Create configuration for sound effect generation
            model_version = "stackadoc/stable-audio-open-1.0:9aff84a639f96d0f7e6081cdea002d15133d0043727f849c40abdd166b7c75a8"
            config = ReplicateAudioConfig(
                version=model_version,
                input={
                    "prompt": effect.prompt,
                    "seconds_total": float(duration),
                    "cfg_scale": 6.0,
                    "steps": 100
                },
                duration=duration
            )
            
            # Start webhook-based prediction
            prediction_id = create_webhook_prediction("sound_effect", effect.effect_id, config)
            prediction_ids.append(prediction_id)
            logger.info(f"✅ Started prediction {prediction_id} for effect: {effect.effect_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start prediction for effect {effect.effect_id}: {e}")
    
    logger.info(f"Started {len(prediction_ids)} parallel predictions")
    return prediction_ids

def wait_for_webhook_completion(db, text_id: int, prediction_ids: List[str], timeout: int = 600) -> int:
    """
    Wait for all webhook predictions to complete and save results to database.
    
    Args:
        db: Database session
        text_id: The ID of the text
        prediction_ids: List of prediction IDs to wait for
        timeout: Maximum time to wait in seconds (default 10 minutes)
        
    Returns:
        Number of effects that successfully received audio data
    """
    if not prediction_ids:
        logger.info("No predictions to wait for")
        return 0
    
    logger.info(f"Waiting for {len(prediction_ids)} webhook predictions to complete...")
    logger.info(f"Prediction IDs: {prediction_ids}")
    
    start_time = time.time()
    poll_interval = 5  # Check every 5 seconds
    
    while time.time() - start_time < timeout:
        # Check database for completed effects
        effects = crud.get_sound_effects_by_text(db, text_id)
        effects_with_audio = [e for e in effects if e.audio_data_b64 and e.audio_data_b64.strip()]
        
        logger.info(f"Progress: {len(effects_with_audio)}/{len(effects)} effects have received audio data")
        
        # Print status for each effect
        for effect in effects:
            has_audio = "✅" if (effect.audio_data_b64 and effect.audio_data_b64.strip()) else "⏳"
            logger.info(f"  {has_audio} {effect.effect_name} (ID: {effect.effect_id})")
        
        # Check if all effects have audio data
        if len(effects_with_audio) == len(effects):
            elapsed_time = time.time() - start_time
            logger.info(f"🎉 All {len(effects)} effects completed in {elapsed_time:.1f} seconds!")
            return len(effects_with_audio)
        
        # Wait before next check
        logger.info(f"Waiting {poll_interval} seconds before next check...")
        time.sleep(poll_interval)
        
        # Refresh database session to get latest data
        db.commit()
    
    # Timeout reached
    elapsed_time = time.time() - start_time
    effects = crud.get_sound_effects_by_text(db, text_id)
    effects_with_audio = [e for e in effects if e.audio_data_b64 and e.audio_data_b64.strip()]
    
    logger.warning(f"⏰ Timeout after {elapsed_time:.1f} seconds. {len(effects_with_audio)}/{len(effects)} effects completed.")
    return len(effects_with_audio)

def generate_and_store_all_effects_sync(db, text_id: int):
    """
    Generate and store audio for all sound effects using parallel webhook processing.
    
    Args:
        db: Database session
        text_id: The ID of the text
    """
    logger.info(f"Starting parallel synchronous generation for text {text_id}")
    
    # Step 1: Start all predictions in parallel with webhooks
    prediction_ids = start_parallel_webhook_predictions(db, text_id)
    
    if not prediction_ids:
        logger.info("No predictions started")
        return
    
    # Step 2: Wait for all webhooks to complete and save results
    success_count = wait_for_webhook_completion(db, text_id, prediction_ids)
    
    total_effects = len(crud.get_sound_effects_by_text(db, text_id))
    logger.info(f"Parallel synchronous generation completed: {success_count}/{total_effects} effects successful")

def main():
    """Main execution function."""
    args = parse_arguments()
    
    db = SessionLocal()
    
    try:
        # Validate that sound effects with prompts exist
        if not validate_sound_effects_exist(db, args.text_id):
            return 1
        
        # Check if server is running to receive webhooks (skip for sync mode)
        print(f"\n🎵 Starting Sound Effects Audio Generation for Text ID: {args.text_id}")
        
        if args.sync:
            print(f"🔄 Using synchronous processing - will wait for results")
        elif not args.skip_server_check:
            print(f"🔍 Checking server health at {settings.BASE_URL}...")
            
            if not check_server_health():
                print(f"\n❌ FastAPI server is not running!")
                print(f"💡 Webhooks cannot be received without a running server.")
                print(f"\n🚀 To start the server, run:")
                print(f"   python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload")
                print(f"\n💡 Or use ngrok to tunnel:")
                print(f"   ngrok http 8000")
                print(f"\n⚠️  Audio will be generated but NOT stored without the server.")
                
                response = input("\nContinue anyway? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Aborted. Start the server and try again.")
                    return 1
                else:
                    print("⚠️  Continuing without server - audio won't be stored")
            else:
                print(f"✅ Server is running and ready to receive webhooks")
        else:
            print(f"⚠️  Skipping server health check - proceeding with generation")
        
        # Step 1: Clear existing audio data from sound effect records
        clear_audio_data(db, args.text_id)
        
        # Step 2: Generate audio using existing prompts
        if args.sync:
            logger.info("Using synchronous processing for sound effects generation")
            generate_and_store_all_effects_sync(db, args.text_id)
        elif args.parallel:
            logger.info("Using parallel processing for sound effects generation")
            generate_and_store_all_effects_parallel(db, args.text_id)
        else:
            logger.info("Using sequential processing for sound effects generation") 
            generate_and_store_all_effects(db, args.text_id)
        
        # Get final counts
        final_effects = crud.get_sound_effects_by_text(db, args.text_id)
        
        if args.sync:
            print(f"\n✅ Sound Effects Audio Generation Completed!")
            print(f"🎯 Sound effects processed: {len(final_effects)}")
            
            # Check how many have audio data
            effects_with_audio = [e for e in final_effects if e.audio_data_b64]
            print(f"🎧 Effects with audio: {len(effects_with_audio)}/{len(final_effects)}")
        else:
            print(f"\n✅ Sound Effects Audio Generation Started!")
            print(f"🎯 Sound effects processed: {len(final_effects)}")
            print(f"🔄 Audio generation triggered via Replicate webhooks (asynchronous)")
        
        if final_effects:
            print(f"\n📋 Sound Effects:")
            for i, effect in enumerate(final_effects, 1):
                has_audio = "✅" if effect.audio_data_b64 else "⏳"
                print(f"  {i}. {has_audio} {effect.effect_name}: {effect.prompt}")
                duration = effect.total_time or "auto"
                print(f"     └── Words {effect.start_word_position}-{effect.end_word_position} | Duration: {duration}s | Rank: {effect.rank}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in sound effects audio generation: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        return 1
        
    finally:
        db.close()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 