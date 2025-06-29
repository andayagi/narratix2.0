#!/usr/bin/env python3
"""
Standalone Text Analysis Script

This script can be run independently to analyze text and store results in the database.

Usage:
    python text_analysis_standalone.py --text-id 123
    python text_analysis_standalone.py --file scripts/input_interactive_e2e.txt
    python text_analysis_standalone.py  # Uses default file

The script will:
1. Delete all related data (characters, segments, Hume voices)
2. Analyze the text using the text_analysis service
3. Save results to the database
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db import crud
from services.text_analysis import process_text_analysis
from utils.logging import get_logger

logger = get_logger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Standalone Text Analysis Service")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--text-id", type=int, help="ID of text to analyze from database")
    group.add_argument("--file", type=str, help="Path to text file to analyze")
    
    parser.add_argument("--create-text", action="store_true", 
                       help="Create new text record if content doesn't exist in database (only used with --file)")
    
    return parser.parse_args()

async def cleanup_existing_data(db, text_id: int):
    """Clean up all existing data for a text_id."""
    logger.info(f"Starting cleanup for text_id {text_id}")
    
    # Import here to avoid circular imports
    from services.text_analysis import _delete_existing_hume_voices, _clear_character_voices_in_db
    
    try:
        # Delete Hume voices
        await _delete_existing_hume_voices(text_id)
        
        # Clear character voice provider IDs
        _clear_character_voices_in_db(db, text_id)
        
        # Delete segments and characters from database
        deleted_segments = crud.delete_segments_by_text(db, text_id)
        deleted_characters = crud.delete_characters_by_text(db, text_id)
        
        logger.info(f"Cleanup completed - Deleted {deleted_characters} characters and {deleted_segments} segments")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise

def read_text_file(file_path: str) -> str:
    """Read content from a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        logger.info(f"Read {len(content)} characters from {file_path}")
        return content
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        raise

async def main():
    """Main execution function."""
    args = parse_arguments()
    
    # Set default file if no arguments provided
    if not args.text_id and not args.file:
        args.file = "scripts/input_interactive_e2e.txt"
        logger.info("No arguments provided, using default file: scripts/input_interactive_e2e.txt")
    
    db = SessionLocal()
    
    try:
        text_id = None
        content = None
        
        if args.text_id:
            # Get text from database
            text_id = args.text_id
            db_text = crud.get_text(db, text_id)
            if not db_text:
                logger.error(f"Text with ID {text_id} not found in database")
                return 1
            content = db_text.content
            logger.info(f"Using text_id {text_id} from database ({len(content)} characters)")
            
        elif args.file:
            # Read text from file
            content = read_text_file(args.file)
            
            # Check if this text content already exists in the database
            existing_text = crud.get_text_by_content(db, content)
            
            if existing_text:
                # Use existing text record
                text_id = existing_text.id
                logger.info(f"Found existing text record with ID {text_id} for this content")
            elif args.create_text:
                # Create new text record
                db_text = crud.create_text(db, content=content)
                text_id = db_text.id
                logger.info(f"Created new text record with ID {text_id}")
            else:
                logger.error("Text content not found in database. Use --create-text to create a new record")
                return 1
        
        if not text_id or not content:
            logger.error("Could not determine text_id and content")
            return 1
        
        # Perform cleanup
        await cleanup_existing_data(db, text_id)
        
        # Run text analysis
        logger.info(f"Starting text analysis for text_id {text_id}")
        result_text = await process_text_analysis(db, text_id, content)
        
        # Get final counts
        characters = crud.get_characters_by_text(db, text_id)
        segments = crud.get_segments_by_text(db, text_id)
        
        logger.info(f"Text analysis completed successfully!")
        logger.info(f"Results: {len(characters)} characters, {len(segments)} segments")
        
        print(f"\n✅ Text Analysis Complete!")
        print(f"📊 Text ID: {text_id}")
        print(f"📝 Content length: {len(content)} characters")
        print(f"👥 Characters created: {len(characters)}")
        print(f"🎯 Segments created: {len(segments)}")
        print(f"✨ Text marked as analyzed: {result_text.analyzed}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in text analysis: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        return 1
        
    finally:
        db.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 