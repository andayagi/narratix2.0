#!/usr/bin/env python3

import argparse
import sys
import os

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services import background_music
from services.audio_analysis import analyze_text_for_audio
from db.database import SessionLocal
from utils.config import validate_config
from utils.logging import get_logger

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Generate background music prompt for a text')
    parser.add_argument('text_id', type=int, help='ID of the text to generate background music for')
    args = parser.parse_args()
    
    # Validate configuration
    if not validate_config():
        logger.error("Configuration validation failed")
        return 1
    
    # Create database session
    db = SessionLocal()
    try:
        # Generate background music prompt using audio analysis
        soundscape, _ = analyze_text_for_audio(args.text_id)
        
        if soundscape:
            # Store the prompt in database
            background_music.update_text_with_music_prompt(db, args.text_id, soundscape)
            
            print(f"Successfully generated background music prompt for text {args.text_id}:")
            print("-" * 80)
            print(soundscape)
            print("-" * 80)
            return 0
        else:
            logger.error(f"Failed to generate background music prompt for text {args.text_id}")
            return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main()) 