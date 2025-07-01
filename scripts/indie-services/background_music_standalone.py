#!/usr/bin/env python3
"""
CLI wrapper for background music service.
Calls the service function directly without duplicating logic.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.background_music import generate_background_music
from utils.logging import get_logger

logger = get_logger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate background music for a specific text")
    parser.add_argument(
        "--text_id", 
        type=int, 
        required=True,
        help="ID of the text to generate background music for"
    )
    return parser.parse_args()

async def main():
    args = parse_arguments()
    logger.info(f"Starting background music generation for text ID {args.text_id}")
    
    try:
        success = await generate_background_music(args.text_id)
        if success:
            logger.info("✅ Background music generation completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Background music generation failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 