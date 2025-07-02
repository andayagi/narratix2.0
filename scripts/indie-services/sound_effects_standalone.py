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
from utils.ngrok_sync import smart_server_health_check, sync_ngrok_url

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
    
    # Check server health and sync ngrok URL if needed
    logger.info("Checking server health and ngrok sync...")
    if not smart_server_health_check():
        logger.error("❌ Server health check failed. Please ensure:")
        logger.error("   1. Local server is running: uvicorn api.main:app --reload")
        logger.error("   2. ngrok is running: ngrok http 8000")
        return False
    
    logger.info("✅ Server is healthy and reachable")
    
    try:
        success = await generate_sound_effects_for_text_parallel(text_id)
        if success:
            logger.info("✅ Sound effects generation completed successfully!")
            return True
        else:
            logger.error("❌ Sound effects generation failed")
            return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1) 