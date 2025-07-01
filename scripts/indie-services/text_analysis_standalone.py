#!/usr/bin/env python3
"""
CLI wrapper for text analysis service.
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
from services.text_analysis import process_text_analysis
from utils.logging import get_logger

logger = get_logger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="CLI wrapper for text analysis service")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--text-id", type=int, help="ID of text to analyze from database")
    group.add_argument("--file", type=str, help="Path to text file to analyze")
    
    parser.add_argument("--create-text", action="store_true", 
                       help="Create new text record if content doesn't exist in database (only used with --file)")
    
    return parser.parse_args()

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
                print(f"❌ Text with ID {text_id} not found")
                sys.exit(1)
            content = db_text.content
            logger.info(f"Using text_id {text_id} from database ({len(content)} characters)")
            
        elif args.file:
            # Read text from file
            content = read_text_file(args.file)
            
            # Check if this text content already exists in the database
            existing_text = crud.get_text_by_content(db, content)
            
            if existing_text:
                text_id = existing_text.id
                logger.info(f"Found existing text record with ID {text_id}")
            elif args.create_text:
                db_text = crud.create_text(db, content=content)
                text_id = db_text.id
                logger.info(f"Created new text record with ID {text_id}")
            else:
                logger.error("Text content not found in database. Use --create-text to create a new record")
                print("❌ Text not found. Use --create-text to create new record")
                sys.exit(1)
        
        if not text_id or not content:
            logger.error("Could not determine text_id and content")
            sys.exit(1)
        
        # Call service function directly (handles cleanup internally)
        result_text = await process_text_analysis(text_id, content)
        
        # Get final counts
        characters = crud.get_characters_by_text(db, text_id)
        segments = crud.get_segments_by_text(db, text_id)
        
        logger.info("✅ Text analysis completed successfully!")
        print(f"✅ Text Analysis Complete!")
        print(f"📊 Text ID: {text_id}")
        print(f"👥 Characters: {len(characters)}")
        print(f"🎯 Segments: {len(segments)}")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main()) 