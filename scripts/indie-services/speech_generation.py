#!/usr/bin/env python3
"""
Standalone Speech Generation Script

This script can be run independently to generate speech audio for text segments 
and store results in the database.

Usage:
    python scripts/indie-services/speech_generation.py --text_id 123

The script will:
1. Check if segments exist for the given text_id
2. Clear existing audio data from segments if present
3. Generate speech using Hume API for all segments
4. Save audio data to the database
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db import crud
from services.speech_generation import generate_text_audio
from utils.logging import get_logger

logger = get_logger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Standalone Speech Generation Service")
    
    parser.add_argument("--text_id", type=int, required=True, 
                       help="ID of text to generate speech for")
    
    return parser.parse_args()

def clear_segment_audio_data(db, text_id: int) -> int:
    """Clear audio data from all segments for a text_id."""
    logger.info(f"Clearing existing audio data for text_id {text_id}")
    
    segments = crud.get_segments_by_text(db, text_id)
    if not segments:
        logger.info(f"No segments found for text_id {text_id}")
        return 0
    
    cleared_count = 0
    for segment in segments:
        if segment.audio_data_b64:
            # Set to None to clear the audio data
            segment.audio_data_b64 = None
            cleared_count += 1
    
    # Commit all changes at once
    if cleared_count > 0:
        db.commit()
    
    logger.info(f"Cleared audio data from {cleared_count} segments")
    return cleared_count

def validate_text_and_segments(db, text_id: int) -> tuple[bool, str]:
    """Validate that text exists and has segments."""
    
    # Check if text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        return False, f"Text with ID {text_id} not found in database"
    
    # Check if segments exist
    segments = crud.get_segments_by_text(db, text_id)
    if not segments:
        return False, f"No segments found for text_id {text_id}. Run text analysis first."
    
    # Check if characters have voice assignments
    characters = crud.get_characters_by_text(db, text_id)
    if not characters:
        return False, f"No characters found for text_id {text_id}. Run text analysis first."
    
    # Check if characters have voice provider IDs
    characters_with_voices = [char for char in characters if char.provider_id]
    if not characters_with_voices:
        return False, f"No characters have voice assignments for text_id {text_id}. Run voice generation first."
    
    logger.info(f"Validation passed: {len(segments)} segments, {len(characters_with_voices)} characters with voices")
    return True, ""

async def main():
    """Main execution function."""
    args = parse_arguments()
    text_id = args.text_id
    
    db = SessionLocal()
    
    try:
        logger.info(f"Starting speech generation for text_id {text_id}")
        
        # Validate text and segments
        is_valid, error_msg = validate_text_and_segments(db, text_id)
        if not is_valid:
            logger.error(error_msg)
            print(f"\n❌ Error: {error_msg}")
            return 1
        
        # Clear existing audio data
        cleared_count = clear_segment_audio_data(db, text_id)
        if cleared_count > 0:
            logger.info(f"Cleared existing audio data from {cleared_count} segments")
        
        # Generate speech audio
        logger.info(f"Starting speech generation process...")
        success = await generate_text_audio(db, text_id)
        
        if success:
            # Get final segment count with audio
            segments = crud.get_segments_by_text(db, text_id)
            segments_with_audio = [seg for seg in segments if seg.audio_data_b64]
            
            logger.info(f"Speech generation completed successfully!")
            logger.info(f"Generated audio for {len(segments_with_audio)} out of {len(segments)} segments")
            
            print(f"\n✅ Speech Generation Complete!")
            print(f"📊 Text ID: {text_id}")
            print(f"🎯 Total segments: {len(segments)}")
            print(f"🎵 Segments with audio: {len(segments_with_audio)}")
            print(f"🧹 Previously cleared: {cleared_count} segments")
            
            return 0
        else:
            logger.error(f"Speech generation failed for text_id {text_id}")
            print(f"\n❌ Speech generation failed. Check logs for details.")
            return 1
        
    except Exception as e:
        logger.error(f"Error in speech generation: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        return 1
        
    finally:
        db.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 