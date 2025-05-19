import os
import subprocess
import base64
import tempfile
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from utils.logging import get_logger
from db import crud

# Initialize logger
logger = get_logger(__name__)

def combine_speech_segments(db: Session, text_id: int, output_dir: str = None, trailing_silence: float = 0.0) -> Optional[str]:
    """
    Combine all speech segments for a given text into a single audio file.
    
    Args:
        db: Database session
        text_id: ID of the text to process
        output_dir: Directory to save the combined audio (defaults to 'output' in current directory)
        trailing_silence: Amount of silence (in seconds) to add after each segment
        
    Returns:
        Path to the combined audio file, or None if error
    """
    try:
        # Get all segments for the text, ordered by sequence
        segments = crud.get_segments_by_text(db, text_id)
        if not segments:
            logger.error(f"No segments found for text ID {text_id}")
            return None
            
        # Set default output directory if not provided
        if not output_dir:
            output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output file name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_audio_path = os.path.join(output_dir, f"combined_speech_{text_id}_{timestamp}.mp3")
        
        # Create temporary files for each segment's audio
        temp_files = []
        segments_with_audio = []
        
        for segment in segments:
            # Skip segments without audio data
            if not segment.audio_data_b64:
                logger.warning(f"Segment {segment.id} doesn't have audio data, skipping")
                continue
                
            # Decode base64 to binary
            try:
                audio_bytes = base64.b64decode(segment.audio_data_b64)
            except Exception as e:
                logger.error(f"Error decoding base64 audio for segment {segment.id}: {str(e)}")
                continue
                
            # Save to temporary file
            temp_fd, temp_file = tempfile.mkstemp(suffix='.mp3')
            os.close(temp_fd)  # Close the file descriptor
            
            with open(temp_file, 'wb') as f:
                f.write(audio_bytes)
                
            temp_files.append(temp_file)
            segments_with_audio.append({
                "file": temp_file,
                "sequence": segment.sequence
            })
            
        if not segments_with_audio:
            logger.error(f"No segments with valid audio data found for text ID {text_id}")
            return None
            
        # Sort segments by sequence
        segments_with_audio.sort(key=lambda x: x["sequence"])
        
        if trailing_silence > 0:
            # Use a simpler approach with the aevalsrc filter to add silence
            temp_silence_files = []
            input_files = []
            
            # Create silence file once
            silence_duration_ms = int(trailing_silence * 1000)
            temp_silence_fd, temp_silence_file = tempfile.mkstemp(suffix='.mp3')
            os.close(temp_silence_fd)
            silence_cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', f'anullsrc=r=44100:cl=stereo:d={trailing_silence}',
                '-c:a', 'libmp3lame',
                '-y',
                temp_silence_file
            ]
            subprocess.run(silence_cmd, capture_output=True)
            temp_silence_files.append(temp_silence_file)
            
            # Create a new list file with silence between segments
            silence_list_path = os.path.join(output_dir, f"filelist_with_silence_{text_id}_{timestamp}.txt")
            with open(silence_list_path, 'w') as f:
                for i, segment in enumerate(segments_with_audio):
                    f.write(f"file '{segment['file']}'\n")
                    # Add silence after each segment except the last one
                    if i < len(segments_with_audio) - 1:
                        f.write(f"file '{temp_silence_file}'\n")
            
            # Use ffmpeg with concat demuxer
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', silence_list_path,
                '-c', 'copy',
                '-y',
                combined_audio_path
            ]
            
            # Add silence_list_path to temp_files for cleanup
            temp_files.append(silence_list_path)
        else:
            # Use the original method with concat if no silence is needed
            file_list_path = os.path.join(output_dir, f"filelist_{text_id}_{timestamp}.txt")
            with open(file_list_path, 'w') as f:
                for segment in segments_with_audio:
                    f.write(f"file '{segment['file']}'\n")
                    
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', file_list_path,
                '-c', 'copy',
                '-y',
                combined_audio_path
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        # Clean up silence files if they were created
        if trailing_silence > 0 and 'temp_silence_files' in locals():
            for silence_file in temp_silence_files:
                if os.path.exists(silence_file):
                    os.remove(silence_file)
        
        # Clean up file list if it was created
        if trailing_silence == 0:
            file_list_path = os.path.join(output_dir, f"filelist_{text_id}_{timestamp}.txt")
            if os.path.exists(file_list_path):
                os.remove(file_list_path)
            
        if result.returncode != 0:
            logger.error(f"Error combining speech segments: {result.stderr}")
            return None
            
        logger.info(f"Successfully combined {len(segments_with_audio)} speech segments into {combined_audio_path}")
        return combined_audio_path
        
    except Exception as e:
        logger.error(f"Error combining speech segments: {str(e)}")
        return None

def export_final_audio(db: Session, text_id: int, output_dir: str = None, bg_volume: float = 1.0, trailing_silence: float = 0.0) -> Optional[str]:
    """
    Create a final audio export by:
    1. Combining all speech segments into one audio file
    2. Adding background music with speech starting 3 seconds after the music
    
    Args:
        db: Database session
        text_id: ID of the text to process
        output_dir: Directory to save output files (defaults to 'output' in current directory)
        bg_volume: Background music volume (0.1 = 10%)
        trailing_silence: Amount of silence (in seconds) to add after each segment
        
    Returns:
        Path to the final audio file, or None if error
    """
    try:
        # Set default output directory if not provided
        if not output_dir:
            output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: Combine speech segments
        logger.info(f"Combining speech segments for text ID {text_id}")
        combined_speech_path = combine_speech_segments(db, text_id, output_dir, trailing_silence)
        if not combined_speech_path:
            logger.error(f"Failed to combine speech segments for text ID {text_id}")
            return None
            
        # Generate output file name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_audio_path = os.path.join(output_dir, f"final_audio_{text_id}_{timestamp}.mp3")
            
        # Step 2: Add background music with speech starting 3 seconds after music
        logger.info(f"Adding background music for text ID {text_id}")
        
        # Use ffmpeg to mix the audio files with offset
        cmd = [
            'ffmpeg',
            '-i', combined_speech_path,  # Speech audio
            '-stream_loop', '-1',  # Loop background music indefinitely
            '-i', 'this_will_be_replaced_with_bg_music',  # Placeholder, will be replaced
            '-filter_complex',
            f'[0:a]adelay=3000|3000[delayed];[1:a]volume={bg_volume}[bg];[delayed][bg]amix=inputs=2:duration=first',
            '-c:a', 'libmp3lame',
            '-q:a', '2',
            '-y',
            final_audio_path
        ]
        
        # Get background music from database
        db_text = crud.get_text(db, text_id)
        if not db_text or not db_text.background_music_audio_b64:
            logger.warning(f"No background music found in database for text {text_id}. Using speech audio without background.")
            # Just copy the combined speech to final output
            import shutil
            shutil.copy(combined_speech_path, final_audio_path)
            return final_audio_path
            
        # Create a temporary file for the background music
        temp_bg_fd, temp_bg_file = tempfile.mkstemp(suffix='.mp3')
        os.close(temp_bg_fd)
        
        try:
            # Decode base64 to binary
            audio_bytes = base64.b64decode(db_text.background_music_audio_b64)
            with open(temp_bg_file, 'wb') as f:
                f.write(audio_bytes)
                
            # Update the command with the actual background music file
            cmd[6] = temp_bg_file
            
            # Run the ffmpeg command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check result
            if result.returncode != 0:
                logger.error(f"Error creating final audio: {result.stderr}")
                return None
                
            logger.info(f"Successfully created final audio: {final_audio_path}")
            return final_audio_path
            
        finally:
            # Clean up temporary files
            if os.path.exists(temp_bg_file):
                os.remove(temp_bg_file)
                
    except Exception as e:
        logger.error(f"Error exporting final audio: {str(e)}")
        return None 