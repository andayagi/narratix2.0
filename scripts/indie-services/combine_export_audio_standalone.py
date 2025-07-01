#!/usr/bin/env python3
"""
CLI wrapper for combine export audio service.
Calls the service function directly without duplicating logic.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db import crud
from services.combine_export_audio import export_final_audio
from utils.logging import get_logger

logger = get_logger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="CLI wrapper for combine export audio service")
    
    parser.add_argument("--text_id", type=int, required=True, 
                       help="ID of text to process from database")
    
    parser.add_argument("--output_dir", type=str, default=None,
                       help="Directory to save output files (defaults to 'output' in current directory)")
    
    parser.add_argument("--trailing_silence", type=float, default=0.0,
                       help="Amount of silence (in seconds) to add after each segment")
    
    parser.add_argument("--bg_volume", type=float, default=0.15,
                       help="Background music volume (0.15 = 15 percent)")
    
    parser.add_argument("--fx_volume", type=float, default=0.3,
                       help="Sound effects volume (0.3 = 30 percent)")
    
    parser.add_argument("--target_lufs", type=float, default=-18.0,
                       help="Target loudness in LUFS (-18.0 is standard for audiobooks)")
    
    return parser.parse_args()

async def main():
    """Main execution function."""
    args = parse_arguments()
    text_id = args.text_id
    
    logger.info(f"Starting combine export audio for text ID {text_id}")
    
    db = SessionLocal()
    
    try:
        # Quick validation
        db_text = crud.get_text(db, text_id)
        if not db_text:
            logger.error(f"Text with ID {text_id} not found in database")
            print(f"\n❌ Error: Text with ID {text_id} not found")
            sys.exit(1)
        
        # Call service function directly
        final_audio_path = await export_final_audio(
            text_id=text_id,
            output_dir=args.output_dir,
            bg_volume=args.bg_volume,
            trailing_silence=args.trailing_silence,
            target_lufs=args.target_lufs,
            fx_volume=args.fx_volume
        )
        
        if final_audio_path:
            logger.info("✅ Combine export audio completed successfully!")
            print(f"✅ Final audio created: {final_audio_path}")
            sys.exit(0)
        else:
            logger.error("❌ Combine export audio failed")
            print("❌ Failed to create final audio")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main()) 