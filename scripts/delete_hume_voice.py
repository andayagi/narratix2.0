#!/usr/bin/env python
"""
Script to delete Hume voices with names that don't contain numbers
Usage: python scripts/delete_hume_voice.py
"""

import os
import sys

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from hume import HumeClient
from utils.config import Settings

def delete_voices_without_numbers():
    """Delete all Hume voices that don't have any numbers in their name"""
    # Setup Hume client
    settings = Settings()
    api_key = os.getenv("HUME_API_KEY") or settings.HUME_API_KEY
    hume_client = HumeClient(api_key=api_key)
    
    try:
        # List all custom voices
        voices = hume_client.tts.voices.list(provider="CUSTOM_VOICE")
        
        # Find and delete voices without numbers in their name
        deleted_count = 0
        for voice in voices:
            if hasattr(voice, "name"):
                # Check if the voice name doesn't contain any digits
                if not any(char.isdigit() for char in voice.name):
                    print(f"Deleting voice '{voice.name}'...")
                    hume_client.tts.voices.delete(name=voice.name)
                    deleted_count += 1
        
        if deleted_count > 0:
            print(f"Successfully deleted {deleted_count} voice(s) without numbers in their name")
        else:
            print(f"No voices found without numbers in their name")
            
    except Exception as e:
        print(f"Error deleting voices: {str(e)}")

if __name__ == "__main__":
    delete_voices_without_numbers() 