#!/usr/bin/env python3
"""
Generate force alignment JSON for audio file with text_id=39
"""
import sys
import json
from db.database import SessionLocal
from db import crud
from services.force_alignment import force_alignment_service

def main():
    # Get database session
    db = SessionLocal()
    
    try:
        # Get text content for text_id=39
        text = crud.get_text(db, 39)
        if not text:
            print("Error: Text with ID 39 not found")
            return
        
        print(f"Running force alignment for text_id=39")
        print(f"Text content: {text.content[:100]}...")
        
        # Audio file path
        audio_file = "tests_one_offs/midsummerr-demo-detective.mp3"
        
        # Run force alignment
        word_timestamps = force_alignment_service.get_word_timestamps(audio_file, text.content)
        
        if word_timestamps:
            # Create output JSON
            result = {
                "text_id": 39,
                "text_content": text.content,
                "audio_file": audio_file,
                "word_timestamps": word_timestamps,
                "timestamp_count": len(word_timestamps)
            }
            
            # Save to file
            output_file = "force_alignment_text39.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"✓ Force alignment completed successfully!")
            print(f"✓ Generated {len(word_timestamps)} word timestamps")
            print(f"✓ Results saved to: {output_file}")
            
        else:
            print("✗ Force alignment failed - no word timestamps generated")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        
    finally:
        db.close()

if __name__ == "__main__":
    main() 