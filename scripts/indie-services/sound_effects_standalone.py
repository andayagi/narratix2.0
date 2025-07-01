#!/usr/bin/env python3
"""
CLI wrapper for sound effects service.
Calls the service function directly without duplicating logic.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.sound_effects import generate_sound_effects_for_text_parallel
from utils.logging import get_logger

logger = get_logger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate sound effects audio for text")
    parser.add_argument(
        "--text_id", 
        type=int, 
        required=True,
        help="ID of text to generate sound effects audio for"
    )
    return parser.parse_args()

async def main():
    args = parse_arguments()
    # argparse converts --text-id to text_id attribute
    text_id = args.text_id
    logger.info(f"Starting sound effects generation for text ID {text_id}")
    
    try:
        success = await generate_sound_effects_for_text_parallel(text_id)
        if success:
            logger.info("✅ Sound effects generation completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Sound effects generation failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 