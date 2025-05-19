import os
import base64
import sys
from sqlalchemy.orm import Session

# Add project root to Python path to allow importing project modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.database import SessionLocal, engine # Assuming your SessionLocal is here
from db import models # Assuming your TextSegment model is here

def download_audio(segment_id: int, output_dir: str = "downloaded_audio"):
    """
    Downloads audio_data_b64 for a given segment ID and saves it as an MP3 file.
    """
    db: Session = SessionLocal()
    output_filename = f"segment_{segment_id}_audio.mp3"
    output_path = os.path.join(PROJECT_ROOT, output_dir, output_filename)

    try:
        print(f"Attempting to fetch segment with ID: {segment_id}")
        segment = db.query(models.TextSegment).filter(models.TextSegment.id == segment_id).first()

        if not segment:
            print(f"Segment with ID {segment_id} not found.")
            return

        if not segment.audio_data_b64:
            print(f"Segment {segment_id} found, but audio_data_b64 is NULL or empty.")
            return

        print(f"Segment {segment_id} found with audio_data_b64. Decoding...")
        
        try:
            audio_bytes = base64.b64decode(segment.audio_data_b64)
        except Exception as e:
            print(f"Error decoding base64 data for segment {segment_id}: {e}")
            return

        # Ensure output directory exists
        os.makedirs(os.path.join(PROJECT_ROOT, output_dir), exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        
        print(f"Successfully saved audio for segment {segment_id} to: {output_path}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    TARGET_SEGMENT_ID = 355 
    # You can change the TARGET_SEGMENT_ID above or pass it as a command-line argument
    # For simplicity, it's hardcoded here.
    
    if len(sys.argv) > 1:
        try:
            segment_id_arg = int(sys.argv[1])
            print(f"Using segment ID from command line argument: {segment_id_arg}")
            download_audio(segment_id_arg)
        except ValueError:
            print(f"Invalid segment ID provided: {sys.argv[1]}. Must be an integer. Using default ID {TARGET_SEGMENT_ID}.")
            download_audio(TARGET_SEGMENT_ID)
    else:
        print(f"No segment ID provided as command line argument. Using default ID {TARGET_SEGMENT_ID}.")
        download_audio(TARGET_SEGMENT_ID) 