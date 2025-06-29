#!/usr/bin/env python3
"""
Standalone Voice Generation Script

This script can be run independently to regenerate character voices for a specific text.

Usage:
    python voice_generation.py --text-id 123

The script will:
1. Find all characters associated with the text_id
2. Delete existing Hume voices that match the pattern *_text_id
3. Generate new voices for all characters in parallel
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path
from typing import List

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db import crud, models
from services.voice_generation import generate_all_character_voices_parallel
from utils.logging import get_logger
from utils.config import Settings

# Import the Hume SDK client
from hume import AsyncHumeClient

logger = get_logger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Standalone Voice Generation Service")
    
    parser.add_argument("--text-id", type=int, required=True, 
                       help="ID of text to generate voices for")
    parser.add_argument("--force", action="store_true",
                       help="Force regeneration even if voices already exist")
    
    return parser.parse_args()

async def delete_existing_hume_voices(text_id: int):
    """Delete all existing Hume voices that match the pattern *_text_id."""
    logger.info(f"Starting deletion of existing Hume voices for text_id {text_id}")
    
    # Get API key
    current_settings = Settings()
    api_key = os.getenv("HUME_API_KEY") or current_settings.HUME_API_KEY
    
    if not api_key:
        logger.error("HUME_API_KEY not found in environment variables or settings")
        raise ValueError("HUME_API_KEY is required")
    
    # Initialize the Hume SDK client
    hume_client = AsyncHumeClient(api_key=api_key)
    
    try:
        # Get all voices from Hume
        voices_response = await hume_client.tts.voices.list()
        all_voices = voices_response.data if hasattr(voices_response, 'data') else []
        
        # Find voices that match the pattern *_text_id
        target_pattern = f"_{text_id}"
        matching_voices = [voice for voice in all_voices if voice.name.endswith(target_pattern)]
        
        logger.info(f"Found {len(matching_voices)} voices matching pattern '*{target_pattern}'")
        
        # Delete matching voices
        deleted_count = 0
        for voice in matching_voices:
            try:
                await hume_client.tts.voices.delete(name=voice.name)
                logger.info(f"Successfully deleted voice: {voice.name}")
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete voice {voice.name}: {str(e)}")
        
        logger.info(f"Deleted {deleted_count} out of {len(matching_voices)} voices")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error deleting Hume voices: {str(e)}")
        raise

def clear_character_voice_ids(db, text_id: int):
    """Clear provider_id and provider fields for all characters of the given text."""
    logger.info(f"Clearing voice IDs for characters in text_id {text_id}")
    
    try:
        # Get all characters for this text
        characters = crud.get_characters_by_text(db, text_id)
        
        cleared_count = 0
        for character in characters:
            if character.provider_id or character.provider:
                # Clear the voice provider information
                crud.update_character_voice(db, character.id, None, None)
                logger.info(f"Cleared voice info for character {character.id} ({character.name})")
                cleared_count += 1
        
        logger.info(f"Cleared voice information for {cleared_count} characters")
        return cleared_count
        
    except Exception as e:
        logger.error(f"Error clearing character voice IDs: {str(e)}")
        raise

async def main():
    """Main execution function."""
    args = parse_arguments()
    
    db = SessionLocal()
    
    try:
        text_id = args.text_id
        
        # Verify text exists
        db_text = crud.get_text(db, text_id)
        if not db_text:
            logger.error(f"Text with ID {text_id} not found in database")
            print(f"❌ Error: Text with ID {text_id} not found")
            return 1
        
        # Get characters for this text
        characters = crud.get_characters_by_text(db, text_id)
        if not characters:
            logger.warning(f"No characters found for text_id {text_id}")
            print(f"⚠️  Warning: No characters found for text_id {text_id}")
            return 0
        
        # Find characters with segments
        speaking_characters = []
        for character in characters:
            segments = db.query(models.TextSegment).filter(models.TextSegment.character_id == character.id).all()
            if segments:
                speaking_characters.append(character)
        
        if not speaking_characters:
            logger.warning(f"No characters with segments found for text_id {text_id}")
            print(f"⚠️  Warning: No speaking characters found for text_id {text_id}")
            return 0
        
        print(f"🎯 Found {len(speaking_characters)} speaking characters for text_id {text_id}")
        
        # Step 1: Delete existing Hume voices
        print(f"🗑️  Deleting existing Hume voices for text_id {text_id}...")
        deleted_voices = await delete_existing_hume_voices(text_id)
        
        # Step 2: Clear character voice IDs in database
        print(f"🧹 Clearing character voice IDs in database...")
        cleared_characters = clear_character_voice_ids(db, text_id)
        
        # Step 3: Generate new voices in parallel
        print(f"🎤 Generating {len(speaking_characters)} character voices in parallel...")
        voice_results = await generate_all_character_voices_parallel(db, text_id)
        
        # Analyze results
        successful_voices = [result for result in voice_results if result[1] is not None]
        failed_voices = [result for result in voice_results if result[1] is None]
        
        print(f"\n✅ Voice Generation Complete!")
        print(f"📊 Text ID: {text_id}")
        print(f"🗑️  Deleted voices: {deleted_voices}")
        print(f"🧹 Cleared character records: {cleared_characters}")
        print(f"✅ Successfully generated: {len(successful_voices)} voices")
        print(f"❌ Failed generations: {len(failed_voices)} voices")
        
        if successful_voices:
            print(f"\n🎉 Successfully generated voices:")
            for char_id, voice_id in successful_voices:
                character = next((c for c in speaking_characters if c.id == char_id), None)
                char_name = character.name if character else f"Character {char_id}"
                print(f"  • {char_name}: {voice_id}")
        
        if failed_voices:
            print(f"\n⚠️  Failed voice generations:")
            for char_id, _ in failed_voices:
                character = next((c for c in speaking_characters if c.id == char_id), None)
                char_name = character.name if character else f"Character {char_id}"
                print(f"  • {char_name} (ID: {char_id})")
        
        return 0 if not failed_voices else 1
        
    except Exception as e:
        logger.error(f"Error in voice generation: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        return 1
        
    finally:
        db.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 