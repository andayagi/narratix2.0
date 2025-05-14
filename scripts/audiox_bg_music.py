#!/usr/bin/env python3
"""
Script to generate background music using AudioX API
"""

import os
import sys
import shutil
import argparse
from datetime import datetime
from gradio_client import Client

def generate_background_music(output_dir="output", duration=20):
    """
    Generate background music using AudioX API
    
    Args:
        output_dir: Directory to save the output
        duration: Duration of the output audio in seconds
        
    Returns:
        Path to the generated audio file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    prompt = """Soft, noir-inspired jazz with muted trumpet and upright bass, creating a slow, tension-building ambiance. Low, intermittent brushed drums at approximately 60 BPM. Incorporate subtle rain-like sound design with soft cymbal brushes and distant, reverberating piano notes. Maintain a melancholic, slightly ominous undertone with gradual volume swells and hushed timbres."""
    
    print(f"Connecting to AudioX API...")
    
    # Initialize the AudioX client
    client = Client("https://zeyue7-audiox.hf.space/")
    
    print(f"Generating background music with prompt: '{prompt}'")
    
    try:
        # Call the AudioX API with the text prompt
        result = client.predict(
            prompt,
            api_name="/generate_cond"
        )
        
        print(f"Result received")
        
        if isinstance(result, tuple) and len(result) >= 2:
            audio_output = result[1]
            
            # Create output path with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"bg_music_noir_jazz_{timestamp}.mp3")
            
            # Copy the file to our output directory
            shutil.copy2(audio_output, output_path)
            
            print(f"Background music generated successfully")
            print(f"Original file: {audio_output}")
            print(f"Saved to: {output_path}")
            
            return output_path
        else:
            print(f"Unexpected result format")
            return None
            
    except Exception as e:
        print(f"Error generating background music: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate background music using AudioX API")
    parser.add_argument("--output", default="output", help="Directory to save the output")
    parser.add_argument("--duration", type=float, default=20, 
                        help="Duration of the output audio in seconds (default: 10)")
    
    args = parser.parse_args()
    
    output_file = generate_background_music(
        output_dir=args.output,
        duration=args.duration
    )
    
    if output_file:
        print(f"Success! Output file: {output_file}")
    else:
        print("Failed to generate background music")
        sys.exit(1) 