import os
import subprocess
import base64
import tempfile
from typing import List, Optional, Dict, Any
from datetime import datetime

from utils.logging import get_logger
from utils.timing import time_it
from db import crud
from db.session_manager import managed_db_session

# Import force alignment dependencies
try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from utils.config import settings

# Initialize logger
logger = get_logger(__name__)

class ForceAlignmentService:
    """Service for generating word-level timestamps using faster-whisper"""
    
    def __init__(self):
        self.model = None
        self.model_size = getattr(settings, 'WHISPERX_MODEL_SIZE', 'base')
        self.compute_type = getattr(settings, 'WHISPERX_COMPUTE_TYPE', 'float32')
        
    def _load_model(self):
        """Load WhisperModel if not already loaded"""
        if self.model is None and WhisperModel is not None:
            try:
                logger.info(f"Loading Whisper model: {self.model_size}")
                self.model = WhisperModel(
                    self.model_size, 
                    device="auto",
                    compute_type=self.compute_type
                )
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {str(e)}")
                self.model = None
        
    def get_word_timestamps(self, audio_file_path: str, text_content: str) -> List[Dict]:
        """
        Get word-level timestamps from audio file
        
        Args:
            audio_file_path: Path to the audio file
            text_content: The text content for reference
            
        Returns:
            List of dictionaries with word, start, and end times
            Format: [{"word": "hello", "start": 0.0, "end": 0.5}, ...]
        """
        if WhisperModel is None:
            logger.warning("faster-whisper not available, returning empty timestamps")
            return []
            
        self._load_model()
        if self.model is None:
            logger.error("Whisper model not available")
            return []
            
        try:
            logger.info(f"Running force alignment on audio file: {audio_file_path}")
            
            # Transcribe with word timestamps
            segments, _ = self.model.transcribe(
                audio_file_path,
                word_timestamps=True,
                language="en"  # Assuming English for now
            )
            
            word_timestamps = []
            for segment in segments:
                if hasattr(segment, 'words') and segment.words:
                    for word_info in segment.words:
                        word_timestamps.append({
                            "word": word_info.word.strip(),
                            "start": word_info.start,
                            "end": word_info.end
                        })
            
            logger.info(f"Generated {len(word_timestamps)} word timestamps")
            return word_timestamps
            
        except Exception as e:
            logger.error(f"Error during force alignment: {str(e)}")
            return []

# Global instance
force_alignment_service = ForceAlignmentService()

def _run_force_alignment_on_combined_audio(combined_audio_path: str, text_content: str, text_id: int) -> bool:
    """
    Run force alignment on the combined audio and store results in database.
    
    Args:
        combined_audio_path: Path to the combined audio file
        text_content: Complete text content
        text_id: ID of the text
        
    Returns:
        True if alignment was successful, False otherwise
    """
    try:
        logger.info(f"Running force alignment for text ID {text_id}")
        
        # Get word timestamps
        word_timestamps = force_alignment_service.get_word_timestamps(combined_audio_path, text_content)
        
        if word_timestamps:
            # Store with current timestamp
            with managed_db_session() as db:
                crud.update_text_word_timestamps(db, text_id, word_timestamps)
            logger.info(f"Successfully completed force alignment for text ID {text_id}, got {len(word_timestamps)} word timestamps")
            return True
        else:
            logger.warning(f"No word timestamps generated for text ID {text_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error running force alignment for text ID {text_id}: {str(e)}")
        return False

def _match_word_position_to_timestamp(word_position: int, word_timestamps: List[Dict]) -> Optional[float]:
    """
    Match a word position (index in text) to its timestamp from force alignment.
    
    Args:
        word_position: Word position in the text (0-based index)
        word_timestamps: List of word timestamps from force alignment
        
    Returns:
        Start timestamp of the word, or None if not found
    """
    if not word_timestamps or word_position < 0:
        return None
        
    # Ensure word_position is within bounds
    if word_position < len(word_timestamps):
        return word_timestamps[word_position]["start"]
    
    # If word_position is beyond our timestamps, return the last word's timestamp
    if word_timestamps:
        logger.warning(f"Word position {word_position} beyond available timestamps ({len(word_timestamps)}), using last word timestamp")
        return word_timestamps[-1]["start"]
    
    return None

@time_it("combine_speech_segments")
async def combine_speech_segments(text_id: int, output_dir: str = None, trailing_silence: float = 0.0) -> Optional[str]:
    """
    Combine all speech segments for a given text into a single audio file.
    This function now includes force alignment before combining.
    
    Args:
        text_id: ID of the text to process
        output_dir: Directory to save the combined audio (defaults to 'output' in current directory)
        trailing_silence: Amount of silence (in seconds) to add after each segment
        
    Returns:
        Path to the combined audio file, or None if error
    """
    try:
        # Get text content for force alignment and segments
        with managed_db_session() as db:
            db_text = crud.get_text(db, text_id)
            if not db_text:
                logger.error(f"Text with ID {text_id} not found")
                return None
            
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
        
        # NEW: Run force alignment on the combined audio
        logger.info(f"Running force alignment on combined audio for text ID {text_id}")
        force_alignment_success = _run_force_alignment_on_combined_audio(
            combined_audio_path, db_text.content, text_id
        )
        
        if not force_alignment_success:
            logger.warning(f"Force alignment failed for text ID {text_id}, but continuing with combined audio")
            
        logger.info(f"Successfully combined {len(segments_with_audio)} speech segments into {combined_audio_path}")
        return combined_audio_path
        
    except Exception as e:
        logger.error(f"Error combining speech segments: {str(e)}")
        return None

@time_it("export_final_audio")
async def export_final_audio(text_id: int, output_dir: str = None, bg_volume: float = 0.15, trailing_silence: float = 0.0, target_lufs: float = -18.0, fx_volume: float = 0.3) -> Optional[str]:
    """
    Create a final audio export by:
    1. Combining all speech segments into one audio file
    2. Normalizing speech to target LUFS
    3. Adding sound effects at their specified start_time positions
    4. Normalizing background music to target LUFS
    5. Mixing normalized audio with speech starting 3 seconds after the music
    6. Continue background music for 3 seconds after speech ends with fade out
    
    Args:
        text_id: ID of the text to process
        output_dir: Directory to save output files (defaults to 'output' in current directory)
        bg_volume: Background music volume (0.15 = 15%, optimal for graphic audio)
        trailing_silence: Amount of silence (in seconds) to add after each segment
        target_lufs: Target loudness in LUFS (-18.0 is standard for audiobooks)
        fx_volume: Sound effects volume (0.3 = 30%, stronger than background music)
        
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
        combined_speech_path = await combine_speech_segments(text_id, output_dir, trailing_silence)
        if not combined_speech_path:
            logger.error(f"Failed to combine speech segments for text ID {text_id}")
            return None
            
        # Generate output file name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_audio_path = os.path.join(output_dir, f"final_audio_{text_id}_{timestamp}.mp3")
        
        # Create temporary files for processing
        temp_files = []
        
        # Step 2: Normalize speech to target LUFS
        temp_norm_speech_fd, temp_norm_speech = tempfile.mkstemp(suffix='.mp3')
        os.close(temp_norm_speech_fd)
        temp_files.append(temp_norm_speech)
        
        norm_speech_cmd = [
            'ffmpeg',
            '-i', combined_speech_path,
            '-af', f'loudnorm=I={target_lufs}:TP=-1:LRA=5',
            '-c:a', 'libmp3lame',
            '-q:a', '2',
            '-y',
            temp_norm_speech
        ]
        result = subprocess.run(norm_speech_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Error normalizing speech: {result.stderr}")
            # Fall back to unnormalized speech
            temp_norm_speech = combined_speech_path
        
        # Step 3: Process sound effects using word position matching
        logger.info(f"Processing sound effects for text ID {text_id}")
        with managed_db_session() as db:
            sound_effects = crud.get_sound_effects_by_text(db, text_id)
            # Get word timestamps from force alignment for sound effect positioning
            db_text = crud.get_text(db, text_id)
            word_timestamps = db_text.word_timestamps if db_text else None
        
        sound_effects_with_audio = []
        
        for effect in sound_effects:
            # Skip effects without audio data
            if not effect.audio_data_b64:
                logger.warning(f"Sound effect {effect.effect_id} ({effect.effect_name}) missing audio data, skipping")
                continue
            
            # Check if word timestamps are available
            if not word_timestamps:
                logger.error(f"No word timestamps available for text ID {text_id}, cannot position sound effects")
                return None
            
            # Check if word position is available
            if effect.start_word_position is None:
                logger.error(f"Sound effect {effect.effect_id} ({effect.effect_name}) missing word position, cannot position sound effect")
                return None
            
            # Determine start time using word position matching
            start_time = _match_word_position_to_timestamp(effect.start_word_position, word_timestamps)
            if start_time is None:
                logger.error(f"Could not match word position {effect.start_word_position} for sound effect '{effect.effect_name}' to timestamp")
                return None
                
            logger.info(f"Matched sound effect '{effect.effect_name}' word position {effect.start_word_position} to timestamp {start_time}s")
                
            try:
                # Decode base64 to binary
                audio_bytes = base64.b64decode(effect.audio_data_b64)
                
                # Save to temporary file
                temp_fx_fd, temp_fx_file = tempfile.mkstemp(suffix='.wav')
                os.close(temp_fx_fd)
                temp_files.append(temp_fx_file)
                
                with open(temp_fx_file, 'wb') as f:
                    f.write(audio_bytes)
                    
                sound_effects_with_audio.append({
                    "file": temp_fx_file,
                    "start_time": start_time,
                    "effect_name": effect.effect_name
                })
                logger.info(f"Prepared sound effect '{effect.effect_name}' at {start_time}s")
                
            except Exception as e:
                logger.error(f"Error processing sound effect {effect.effect_id}: {str(e)}")
                continue
        
        # Step 4: Get background music from database
        with managed_db_session() as db:
            db_text = crud.get_text(db, text_id)
            if not db_text or not db_text.background_music_audio_b64:
                logger.warning(f"No background music found for text {text_id}")
                # Mix speech with sound effects only
                if sound_effects_with_audio:
                    return _mix_speech_with_sound_effects(temp_norm_speech, sound_effects_with_audio, fx_volume, final_audio_path, temp_files)
                else:
                    # Return normalized speech only
                    return temp_norm_speech
            
            # Extract background music data for processing
            bg_music_data = db_text.background_music_audio_b64
        
        # Step 5: Process background music
        temp_bg_fd, temp_bg_file = tempfile.mkstemp(suffix='.mp3')
        os.close(temp_bg_fd)
        temp_files.append(temp_bg_file)
        
        try:
            audio_bytes = base64.b64decode(bg_music_data)
            with open(temp_bg_file, 'wb') as f:
                f.write(audio_bytes)
            
            # Normalize background music to same target LUFS
            temp_norm_bg_fd, temp_norm_bg = tempfile.mkstemp(suffix='.mp3')
            os.close(temp_norm_bg_fd)
            temp_files.append(temp_norm_bg)
            
            norm_bg_cmd = [
                'ffmpeg',
                '-i', temp_bg_file,
                '-af', f'loudnorm=I={target_lufs}:TP=-1:LRA=5',
                '-c:a', 'libmp3lame',
                '-q:a', '2',
                '-y',
                temp_norm_bg
            ]
            result = subprocess.run(norm_bg_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Error normalizing background music: {result.stderr}")
                temp_norm_bg = temp_bg_file
            
            # Step 6: Get duration of speech audio
            duration_cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                temp_norm_speech
            ]
            result = subprocess.run(duration_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Error getting speech duration: {result.stderr}")
                speech_duration = 0
            else:
                try:
                    speech_duration = float(result.stdout.strip())
                except (ValueError, TypeError):
                    logger.error("Could not parse speech duration")
                    speech_duration = 0
            
            # Step 7: Build complex filter for mixing all layers
            speech_start_delay_s = 3
            fade_out_duration_s = 3
            fade_start_time_s = speech_start_delay_s + speech_duration
            
            # Start building filter complex
            filter_parts = []
            input_files = [temp_norm_speech]
            
            # Background music with loop and fade
            filter_parts.append(f"amovie='{temp_norm_bg}':loop=0,asetpts=N/SR/TB[bg_raw]")
            filter_parts.append(f"[0:a]adelay={speech_start_delay_s * 1000}|{speech_start_delay_s * 1000}[delayed_speech]")
            filter_parts.append(f"[bg_raw]volume={bg_volume},afade=t=out:st={fade_start_time_s}:d={fade_out_duration_s}[bg]")
            filter_parts.append(f"[delayed_speech]apad=pad_dur={fade_out_duration_s}[padded_speech]")
            
            # Add sound effects
            mix_inputs = ["[padded_speech]", "[bg]"]
            if sound_effects_with_audio:
                for i, fx in enumerate(sound_effects_with_audio):
                    fx_label = f"fx{i}"
                    # Add speech delay offset to sound effect timing to keep them synchronized
                    fx_total_delay_s = fx["start_time"] + speech_start_delay_s
                    delay_ms = int(fx_total_delay_s * 1000)
                    filter_parts.append(f"amovie='{fx['file']}',volume={fx_volume},adelay={delay_ms}|{delay_ms}[{fx_label}]")
                    mix_inputs.append(f"[{fx_label}]")
                    logger.info(f"Added sound effect '{fx['effect_name']}' at {fx_total_delay_s}s (original: {fx['start_time']}s + {speech_start_delay_s}s speech delay) with volume {fx_volume}")
            
            # Final mix
            num_inputs = len(mix_inputs)
            filter_parts.append(f"{''.join(mix_inputs)}amix=inputs={num_inputs}:duration=first")
            
            filter_complex = ";".join(filter_parts)
            
            mix_cmd = [
                'ffmpeg',
                '-i', temp_norm_speech,
                '-filter_complex', filter_complex,
                '-c:a', 'libmp3lame',
                '-q:a', '2',
                '-y',
                final_audio_path
            ]
            
            result = subprocess.run(mix_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Error creating final mixed audio: {result.stderr}")
                return temp_norm_speech
                
            logger.info(f"Successfully created final audio: {final_audio_path} at target {target_lufs} LUFS with {bg_volume*100}% background music, {fx_volume*100}% sound effects, and 3-second fade out")
            return final_audio_path
            
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            return combined_speech_path
            
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        logger.warning(f"Failed to remove temp file {temp_file}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error exporting final audio: {str(e)}")
        return None

def _mix_speech_with_sound_effects(speech_file: str, sound_effects: List[dict], fx_volume: float, output_path: str, temp_files: List[str]) -> str:
    """
    Helper function to mix speech with sound effects only (no background music).
    
    Args:
        speech_file: Path to the speech audio file
        sound_effects: List of sound effect dictionaries with file paths and timing
        fx_volume: Volume for sound effects
        output_path: Output file path
        temp_files: List to track temporary files for cleanup
        
    Returns:
        Path to the mixed audio file
    """
    try:
        # Build filter for mixing speech with sound effects
        filter_parts = []
        mix_inputs = ["[0:a]"]
        
        # Add sound effects
        for i, fx in enumerate(sound_effects):
            fx_label = f"fx{i}"
            delay_ms = int(fx["start_time"] * 1000)
            filter_parts.append(f"amovie='{fx['file']}',volume={fx_volume},adelay={delay_ms}|{delay_ms}[{fx_label}]")
            mix_inputs.append(f"[{fx_label}]")
        
        # Final mix
        num_inputs = len(mix_inputs)
        filter_parts.append(f"{''.join(mix_inputs)}amix=inputs={num_inputs}:duration=first")
        
        filter_complex = ";".join(filter_parts)
        
        mix_cmd = [
            'ffmpeg',
            '-i', speech_file,
            '-filter_complex', filter_complex,
            '-c:a', 'libmp3lame',
            '-q:a', '2',
            '-y',
            output_path
        ]
        
        result = subprocess.run(mix_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Error mixing speech with sound effects: {result.stderr}")
            return speech_file
            
        logger.info(f"Successfully mixed speech with {len(sound_effects)} sound effects at {fx_volume*100}% volume")
        return output_path
        
    except Exception as e:
        logger.error(f"Error mixing speech with sound effects: {str(e)}")
        return speech_file 