"""
Service for analyzing text, generating, and managing sound effects.

This service is designed to be completely independent of text analysis for speech generation.
It analyzes the full text content to identify opportunities for cinematic sound effects
and generates them using an AI audio generation service (AudioX).
"""
import re
import base64
import os
import json
import subprocess
import tempfile
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
import anthropic
import replicate
from utils.logging import get_logger
from utils.config import settings
from utils.http_client import get_sync_client
from db import crud
from utils.timing import time_it

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=settings.ANTHROPIC_API_KEY,
)

logger = get_logger(__name__)

# Placeholder for an Anthropic client, assuming one will be available.
# from clients.anthropic_client import get_anthropic_client 

# AudioX client is no longer used, switched to Replicate.

def delete_existing_sound_effects(db: Session, text_id: int) -> int:
    """
    Delete all existing sound effects for a given text_id.
    
    Args:
        db: Database session.
        text_id: The ID of the text to clean up.
        
    Returns:
        Number of deleted sound effects.
    """
    deleted_count = crud.delete_sound_effects_by_text(db, text_id)
    logger.info(f"Deleted {deleted_count} existing sound effects for text {text_id}")
    return deleted_count

@time_it("analyze_text_for_sound_effects")
def analyze_text_for_sound_effects(
    db: Session, 
    text_id: int
) -> List[Dict]:
    """
    Analyze text for potential sound effects using unified audio analysis.
    
    Args:
        db: Database session.
        text_id: The ID of the text to analyze.
        
    Returns:
        A list of sound effect specifications.
    """
    from services.audio_analysis import analyze_text_for_audio
    
    logger.info(f"Starting sound effects analysis for text {text_id}")
    
    # Delete any existing sound effects for this text first
    delete_existing_sound_effects(db, text_id)
    
    try:
        # Use unified analysis to get sound effects
        _, sound_effects = analyze_text_for_audio(db, text_id)
        
        if not sound_effects:
            logger.info(f"No sound effects identified for text {text_id}")
            return []
        
        logger.info(f"Claude identified {len(sound_effects)} potential sound effects for text {text_id}")
        
        # Apply text length filtering
        db_text = crud.get_text(db, text_id)
        text_length = len(db_text.content)
        max_effects = max(1, text_length // 200)
        
        logger.info(f"Text length: {text_length} characters, allowing max {max_effects} sound effects")
        
        # Sort by rank and limit
        for effect in sound_effects:
            try:
                effect['rank'] = int(effect.get('rank', 999))
            except (ValueError, TypeError):
                effect['rank'] = 999
        
        sound_effects.sort(key=lambda x: x['rank'])
        sound_effects = sound_effects[:max_effects]
        
        logger.info(f"After filtering by text length and rank, storing {len(sound_effects)} sound effects")
        
        processed_effects = []
        
        # Store the sound effects
        for effect in sound_effects:
            try:
                start_word_number = effect.get('start_word_number')
                end_word_number = effect.get('end_word_number')
                rank = effect.get('rank')
                
                # Calculate total_time based on word count
                total_time = None
                if start_word_number is not None and end_word_number is not None:
                    word_count = end_word_number - start_word_number + 1
                    total_time = max(1, word_count)
                else:
                    total_time = 2  # Default 2 seconds
                
                crud.create_sound_effect(
                    db=db,
                    effect_name=effect['effect_name'],
                    text_id=text_id,
                    start_word=effect['start_word'],
                    end_word=effect['end_word'],
                    start_word_position=start_word_number,
                    end_word_position=end_word_number,
                    prompt=effect['prompt'],
                    audio_data_b64="",
                    start_time=None,
                    end_time=None,
                    total_time=total_time,
                    rank=rank
                )
                logger.info(f"Stored sound effect '{effect['effect_name']}' in database with word positions: {start_word_number}-{end_word_number}")
                processed_effects.append(effect)
            except Exception as e:
                logger.error(f"Error storing sound effect '{effect['effect_name']}': {e}")
        
        return processed_effects
        
    except Exception as e:
        logger.error(f"Error in sound effects analysis: {e}")
        return []

@time_it("generate_and_store_sound_effect")
def generate_and_store_effect(db: Session, effect_id: int):
    """
    Triggers webhook-based audio generation for a sound effect.
    
    Args:
        db: Database session.
        effect_id: The ID of the sound effect to generate.
    """
    from services.replicate_audio import create_webhook_prediction, ReplicateAudioConfig
    
    effect = crud.get_sound_effect(db, effect_id=effect_id)
    if not effect:
        logger.error(f"Cannot generate audio for non-existent effect_id {effect_id}")
        return

    logger.info(f"Starting webhook-based audio generation for effect: {effect.effect_name} (ID: {effect_id})")

    # Use the pre-calculated total_time from the database
    duration = effect.total_time
    if duration is None or duration <= 0:
        logger.error(f"Invalid duration ({duration}) for effect {effect_id}. Aborting generation.")
        return

    logger.info(f"Triggering generation for '{effect.effect_name}' with prompt: '{effect.prompt}' and duration: {duration}s")
    
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
        
        # Trigger webhook-based generation
        prediction_id = create_webhook_prediction("sound_effect", effect_id, config)
        logger.info(f"Successfully triggered webhook generation for effect {effect_id}, prediction ID: {prediction_id}")
        
    except Exception as e:
        logger.error(f"Failed to trigger webhook generation for effect {effect_id}: {e}")
        raise

    logger.info(f"Webhook generation triggered for effect {effect_id}, processing will continue asynchronously") 

@time_it("generate_and_store_all_sound_effects")
def generate_and_store_all_effects(db: Session, text_id: int):
    """
    Generates and stores audio for all sound effects of a given text.
    
    Args:
        db: Database session.
        text_id: The ID of the text to process.
    """
    logger.info(f"Starting audio generation for all effects of text {text_id}")
    
    # Get all sound effects for the given text
    effects_to_process = crud.get_sound_effects_by_text(db, text_id)
    
    # Generate and store audio for each effect
    for effect in effects_to_process:
        generate_and_store_effect(db, effect.effect_id)
    
    logger.info(f"Finished generating audio for all {len(effects_to_process)} effects for text {text_id}")

@time_it("generate_and_store_all_sound_effects_parallel")
def generate_and_store_all_effects_parallel(db: Session, text_id: int):
    """
    Generates and stores audio for all sound effects in parallel using threading.
    
    Args:
        db: Database session.
        text_id: The ID of the text to process.
    """
    import concurrent.futures
    import threading
    from db.database import SessionLocal
    
    logger.info(f"Starting PARALLEL audio generation for all effects of text {text_id}")
    
    # Get all sound effects for the given text
    effects_to_process = crud.get_sound_effects_by_text(db, text_id)
    
    if not effects_to_process:
        logger.info(f"No sound effects to generate for text {text_id}")
        return
    
    def generate_single_effect(effect_id: int):
        """Worker function to generate a single effect with its own DB session"""
        worker_db = SessionLocal()
        try:
            generate_and_store_effect(worker_db, effect_id)
        finally:
            worker_db.close()
    
    # Use ThreadPoolExecutor for parallel Replicate API calls
    max_workers = min(len(effects_to_process), 3)  # Limit to 3 concurrent Replicate calls
    logger.info(f"Using {max_workers} parallel workers for {len(effects_to_process)} sound effects")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all sound effect generation tasks
        future_to_effect = {
            executor.submit(generate_single_effect, effect.effect_id): effect 
            for effect in effects_to_process
        }
        
        # Wait for all to complete and log results
        completed = 0
        failed = 0
        for future in concurrent.futures.as_completed(future_to_effect):
            effect = future_to_effect[future]
            try:
                future.result()  # This will raise any exception that occurred
                completed += 1
                logger.info(f"✅ Completed sound effect '{effect.effect_name}' ({completed}/{len(effects_to_process)})")
            except Exception as e:
                failed += 1
                logger.error(f"❌ Failed sound effect '{effect.effect_name}': {e}")
    
    logger.info(f"Finished PARALLEL generation: {completed} completed, {failed} failed out of {len(effects_to_process)} total")


@time_it("process_sound_effects")
def process_sound_effects(db: Session, text_id: int):
    """
    Full end-to-end process for analyzing and generating sound effects.
    
    Args:
        db: Database session.
        text_id: The ID of the text to process.
    """
    logger.info(f"Starting sound effect processing for text {text_id}")
    
    # Step 1: Analyze text and create sound effect records
    analyze_text_for_sound_effects(db, text_id)
    
    # Step 2: Generate and store audio for all effects
    generate_and_store_all_effects(db, text_id)
    
    logger.info(f"Completed sound effect processing for text {text_id}")

@time_it("process_sound_effects_parallel")
def process_sound_effects_parallel(db: Session, text_id: int):
    """
    Full end-to-end process with PARALLEL sound effect generation.
    
    Args:
        db: Database session.
        text_id: The ID of the text to process.
    """
    logger.info(f"Starting PARALLEL sound effect processing for text {text_id}")
    
    # Step 1: Analyze text and create sound effect records
    analyze_text_for_sound_effects(db, text_id)
    
    # Step 2: Generate and store audio for all effects IN PARALLEL
    generate_and_store_all_effects_parallel(db, text_id)
    
    logger.info(f"Completed PARALLEL sound effect processing for text {text_id}")

# New async versions for parallel processing
@time_it("async_generate_and_store_all_sound_effects")
async def generate_and_store_all_effects_async(db: Session, text_id: int):
    """
    Async version of generate_and_store_all_effects with TRUE parallel processing.
    
    Args:
        db: Database session.
        text_id: The ID of the text to process.
    """
    import asyncio
    
    # Run the PARALLEL synchronous function in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, generate_and_store_all_effects_parallel, db, text_id)

@time_it("async_process_sound_effects")
async def process_sound_effects_async(db: Session, text_id: int):
    """
    Async version of process_sound_effects with TRUE parallel processing.
    
    Args:
        db: Database session.
        text_id: The ID of the text to process.
    """
    import asyncio
    
    # Run the PARALLEL synchronous function in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, process_sound_effects_parallel, db, text_id)