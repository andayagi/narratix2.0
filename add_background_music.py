#!/usr/bin/env python3
import subprocess
import os
import math
from datetime import datetime

def add_background_music(input_audio, bg_music, output_audio, bg_volume=0.1, bg_offset=3):
    """
    Add background music to an audio file using ffmpeg.
    
    Args:
        input_audio (str): Path to the input audio file
        bg_music (str): Path to the background music file
        output_audio (str): Path to save the output audio file
        bg_volume (float): Volume level for background music (0.1 = 10%)
        bg_offset (int): Number of seconds to start background music before narration
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(output_audio)
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the duration of the input audio
    duration_cmd = [
        'ffprobe', 
        '-v', 'error', 
        '-show_entries', 'format=duration', 
        '-of', 'default=noprint_wrappers=1:nokey=1', 
        input_audio
    ]
    
    result = subprocess.run(duration_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error getting duration: {result.stderr}")
        return False
    
    input_duration = float(result.stdout.strip())
    print(f"Input audio duration: {input_duration} seconds")
    
    # Now mix the background with the original audio
    cmd = [
        'ffmpeg',
        '-i', input_audio,
        '-stream_loop', '-1',  # Loop background music indefinitely
        '-i', bg_music,
        '-filter_complex',
        f'[0:a]adelay={bg_offset*1000}|{bg_offset*1000}[main];[1:a]volume={bg_volume}[bg];[main][bg]amix=inputs=2:duration=first',
        '-c:a', 'libmp3lame',
        '-q:a', '2',
        '-y',
        output_audio
    ]
    
    print("Creating mixed audio with looped background music...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    else:
        print(f"Successfully created output file: {output_audio}")
        return True

if __name__ == "__main__":
    # Paths
    input_audio = "/Users/anatburg/Narratix2.0/audio_files/2025-05-13/20250513_144713_27_inter_e2e.mp3"
    bg_music = "/Users/anatburg/Narratix2.0/output/replicate-prediction-m439e6pzmxrme0cpscy9dwcvy0.wav"
    output_dir = "/Users/anatburg/Narratix2.0/output"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"test_with_bg_music_{timestamp}.mp3")
    
    # Add background music at 10% volume with 3-second offset
    add_background_music(input_audio, bg_music, output_path, bg_volume=0.05, bg_offset=3) 