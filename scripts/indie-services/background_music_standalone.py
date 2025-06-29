#!/usr/bin/env python3
"""
Standalone script for generating background music for a specific text.

Usage: python background_music_standalone.py --text_id <ID>

This script:
1. Receives a text_id using a flag
2. Checks if there's an existing prompt and audio 
3. If audio exists - deletes it
4. Creates a call to replicate and awaits its response via webhook (2-3 minutes)
5. Saves the audio to the database
"""

import argparse
import asyncio
import sys
import time
from typing import Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from db.database import get_db
from db import crud
from services.background_music import generate_background_music_prompt, generate_background_music
from utils.logging import get_logger

logger = get_logger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate background music for a specific text"
    )
    parser.add_argument(
        "--text_id", 
        type=int, 
        required=True,
        help="ID of the text to generate background music for"
    )
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=300,  # 5 minutes
        help="Timeout in seconds to wait for webhook response (default: 300)"
    )
    parser.add_argument(
        "--poll_interval", 
        type=int, 
        default=10,
        help="Polling interval in seconds (default: 10)"
    )
    return parser.parse_args()

def check_existing_data(db: Session, text_id: int) -> tuple[bool, bool, Optional[str]]:
    """
    Check if text has existing prompt and audio.
    
    Returns:
        Tuple of (has_prompt, has_audio, prompt_text)
    """
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise ValueError(f"Text with ID {text_id} not found")
    
    has_prompt = bool(db_text.background_music_prompt)
    has_audio = bool(db_text.background_music_audio_b64)
    prompt_text = db_text.background_music_prompt
    
    return has_prompt, has_audio, prompt_text

def delete_existing_audio(db: Session, text_id: int) -> bool:
    """Delete existing background music audio from database."""
    try:
        db_text = crud.get_text(db, text_id)
        if db_text and db_text.background_music_audio_b64:
            logger.info(f"Deleting existing background music audio for text {text_id}")
            db_text.background_music_audio_b64 = None
            db.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting existing audio: {e}")
        return False

def wait_for_audio_generation(db: Session, text_id: int, timeout: int, poll_interval: int) -> bool:
    """
    Poll database waiting for background music audio to be stored.
    
    Args:
        db: Database session
        text_id: Text ID to check
        timeout: Maximum time to wait in seconds
        poll_interval: How often to check in seconds
        
    Returns:
        True if audio was generated and stored, False if timeout
    """
    start_time = time.time()
    
    logger.info(f"Waiting for background music generation (timeout: {timeout}s, poll interval: {poll_interval}s)")
    
    while time.time() - start_time < timeout:
        # Refresh the database session
        db.rollback()  # Clear any pending transactions
        
        db_text = crud.get_text(db, text_id)
        if db_text and db_text.background_music_audio_b64:
            elapsed = time.time() - start_time
            logger.info(f"Background music generation completed after {elapsed:.1f} seconds")
            return True
        
        logger.info(f"Still waiting... ({time.time() - start_time:.1f}s elapsed)")
        time.sleep(poll_interval)
    
    logger.error(f"Timeout waiting for background music generation after {timeout} seconds")
    return False

def main():
    """Main execution function."""
    args = parse_arguments()
    text_id = args.text_id
    timeout = args.timeout
    poll_interval = args.poll_interval
    
    logger.info(f"Starting background music generation for text ID {text_id}")
    
    # Get database session
    try:
        db = next(get_db())
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)
    
    try:
        # Step 1: Check if text exists and get existing data
        logger.info("Step 1: Checking existing data...")
        has_prompt, has_audio, prompt_text = check_existing_data(db, text_id)
        
        logger.info(f"Existing prompt: {'Yes' if has_prompt else 'No'}")
        logger.info(f"Existing audio: {'Yes' if has_audio else 'No'}")
        
        if has_prompt:
            logger.info(f"Current prompt: {prompt_text}")
        
        # Step 2: Delete existing audio if it exists
        if has_audio:
            logger.info("Step 2: Deleting existing audio...")
            if delete_existing_audio(db, text_id):
                logger.info("Successfully deleted existing audio")
            else:
                logger.warning("Failed to delete existing audio")
        else:
            logger.info("Step 2: No existing audio to delete")
        
        # Step 3: Generate prompt if needed
        if not has_prompt:
            logger.info("Step 3: Generating background music prompt...")
            prompt = generate_background_music_prompt(db, text_id)
            if not prompt:
                logger.error("Failed to generate background music prompt")
                sys.exit(1)
            logger.info(f"Generated prompt: {prompt}")
        else:
            logger.info("Step 3: Using existing prompt")
        
        # Step 4: Trigger background music generation via Replicate webhook
        logger.info("Step 4: Triggering background music generation...")
        success = generate_background_music(db, text_id)
        if not success:
            logger.error("Failed to trigger background music generation")
            sys.exit(1)
        
        logger.info("Successfully triggered background music generation webhook")
        
        # Step 5: Wait for webhook response and audio storage
        logger.info("Step 5: Waiting for background music generation to complete...")
        if wait_for_audio_generation(db, text_id, timeout, poll_interval):
            logger.info("✅ Background music generation completed successfully!")
            
            # Get final audio size for confirmation
            db_text = crud.get_text(db, text_id)
            if db_text and db_text.background_music_audio_b64:
                audio_size = len(db_text.background_music_audio_b64)
                logger.info(f"Generated audio size: {audio_size} bytes (base64)")
            
        else:
            logger.error("❌ Background music generation timed out or failed")
            sys.exit(1)
            
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main() 