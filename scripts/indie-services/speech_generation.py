#!/usr/bin/env python3
"""
CLI wrapper for speech generation service.
Calls the service function directly without duplicating logic.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.speech_generation import generate_text_audio
from utils.logging import get_logger
from db.database import SessionLocal
from db import crud

logger = get_logger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate speech audio for text segments")
    parser.add_argument("--text_id", type=int, required=True, 
                       help="ID of text to generate speech for")
    return parser.parse_args()

async def main():
    args = parse_arguments()
    logger.info(f"Starting speech generation for text_id {args.text_id}")
    
    try:
        # Basic validation
        db = SessionLocal()
        try:
            db_text = crud.get_text(db, args.text_id)
            if not db_text:
                logger.error(f"Text with ID {args.text_id} not found")
                print(f"❌ Error: Text with ID {args.text_id} not found")
                sys.exit(1)
        finally:
            db.close()

        success = await generate_text_audio(args.text_id)
        if success:
            logger.info("✅ Speech generation completed successfully!")
            print("✅ Speech Generation Complete!")
            sys.exit(0)
        else:
            logger.error("❌ Speech generation failed")
            print("❌ Speech generation failed. Check logs for details.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 