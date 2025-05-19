#!/usr/bin/env python3
import argparse
import os
import sys
import base64
from datetime import datetime
from sqlalchemy.orm import Session

# Add parent directory to Python path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db import crud
from utils.logging import get_logger

logger = get_logger(__name__)

def export_background_music(db: Session, text_id: int, output_dir: str = "audio_files") -> str:
    """
    Export background music from database to file
    
    Args:
        db: Database session
        text_id: ID of the text to export background music for
        output_dir: Directory to save the audio file
        
    Returns:
        Path to the exported audio file
    """
    # Get text from database
    db_text = crud.get_text(db, text_id)
    if not db_text or not db_text.background_music_audio_b64:
        logger.error(f"No background music found for text ID {text_id}")
        return None
        
    # Create output directory structure
    text_dir = os.path.join(output_dir, str(text_id))
    os.makedirs(text_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(text_dir, f"background_music_{timestamp}.mp3")
    
    try:
        # Decode base64 and write to file
        audio_bytes = base64.b64decode(db_text.background_music_audio_b64)
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)
            
        logger.info(f"Successfully exported background music to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error exporting background music: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Export background music from database")
    parser.add_argument("text_id", type=int, help="ID of the text to export background music for")
    parser.add_argument("--output-dir", "-o", default="audio_files", help="Directory to save output files")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        result = export_background_music(db, args.text_id, args.output_dir)
        if result:
            print(f"Successfully exported background music: {result}")
            return 0
        else:
            print("Failed to export background music. Check logs for details.")
            return 1
    except Exception as e:
        logger.error(f"Error in export_background_music.py: {str(e)}")
        print(f"Error: {str(e)}")
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main()) 