#!/usr/bin/env python3
"""
CLI wrapper for audio analysis service.
Calls the service function directly without duplicating logic.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.audio_analysis import analyze_text_for_audio
from utils.logging import get_logger

logger = get_logger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Analyze text for audio elements")
    parser.add_argument(
        "--text_id", 
        type=int, 
        required=True,
        help="ID of text to analyze from database"
    )
    return parser.parse_args()

def main():
    args = parse_arguments()
    logger.info(f"Starting audio analysis for text ID {args.text_id}")
    
    try:
        soundscape, sound_effects = analyze_text_for_audio(args.text_id)
        
        if soundscape or sound_effects:
            logger.info("✅ Audio analysis completed successfully!")
            logger.info(f"Soundscape: {'Generated' if soundscape else 'None'}")
            logger.info(f"Sound effects: {len(sound_effects) if sound_effects else 0}")
            sys.exit(0)
        else:
            logger.error("❌ Audio analysis failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 