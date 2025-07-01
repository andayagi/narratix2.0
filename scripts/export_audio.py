#!/usr/bin/env python3
import argparse
import os
import sys
from sqlalchemy.orm import Session

# Add parent directory to Python path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from services.combine_export_audio import export_final_audio
from utils.logging import get_logger

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Export final audio by combining speech segments with background music")
    
    parser.add_argument("text_id", type=int, help="ID of the text to process")
    parser.add_argument("--output-dir", "-o", default=None, help="Directory to save output files")
    parser.add_argument("--bg-volume", "-v", type=float, default=0.1, help="Background music volume (0.1 = 10%)")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        result = await export_final_audio(args.text_id, args.output_dir, args.bg_volume)
        if result:
            print(f"Successfully exported final audio: {result}")
            return 0
        else:
            print("Failed to export final audio. Check logs for details.")
            return 1
    except Exception as e:
        logger.error(f"Error in export_audio.py: {str(e)}")
        print(f"Error: {str(e)}")
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main()) 