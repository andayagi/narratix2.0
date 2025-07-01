#!/usr/bin/env python3
"""
CLI wrapper for voice generation service.
Calls the service function directly without duplicating logic.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.voice_generation import generate_all_character_voices_parallel
from utils.logging import get_logger
from db.database import SessionLocal
from db import crud

logger = get_logger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate character voices for text")
    parser.add_argument("--text-id", type=int, required=True, 
                       help="ID of text to generate voices for")
    parser.add_argument("--force", action="store_true",
                       help="Force regeneration even if voices already exist")
    return parser.parse_args()

async def main():
    args = parse_arguments()
    logger.info(f"Starting voice generation for text_id {args.text_id}")
    
    try:
        # Basic validation
        db = SessionLocal()
        try:
            db_text = crud.get_text(db, args.text_id)
            if not db_text:
                logger.error(f"Text with ID {args.text_id} not found")
                print(f"❌ Error: Text with ID {args.text_id} not found")
                sys.exit(1)
                
            characters = crud.get_characters_by_text(db, args.text_id)
            if not characters:
                logger.warning(f"No characters found for text_id {args.text_id}")
                print(f"⚠️  Warning: No characters found for text_id {args.text_id}")
                sys.exit(0)
        finally:
            db.close()

        voice_results = await generate_all_character_voices_parallel(args.text_id)
        
        # Analyze results
        successful_voices = [result for result in voice_results if result[1] is not None]
        failed_voices = [result for result in voice_results if result[1] is None]
        
        print(f"✅ Voice Generation Complete!")
        print(f"📊 Text ID: {args.text_id}")
        print(f"✅ Successfully generated: {len(successful_voices)} voices")
        print(f"❌ Failed generations: {len(failed_voices)} voices")
        
        if successful_voices:
            logger.info(f"Generated {len(successful_voices)} voices successfully")
        
        if failed_voices:
            logger.warning(f"Failed to generate {len(failed_voices)} voices")
            
        sys.exit(0 if not failed_voices else 1)
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 