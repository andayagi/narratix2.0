import os
import tempfile
import base64
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import logging

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from utils.logging import get_logger
from utils.config import settings
from services.combine_export_audio import combine_speech_segments
from db import crud

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
    
    def align_audio_from_base64(self, audio_data_b64: str, text_content: str) -> List[Dict]:
        """
        Get word-level timestamps from base64 audio data
        
        Args:
            audio_data_b64: Base64 encoded audio data
            text_content: The text content for reference
            
        Returns:
            List of dictionaries with word, start, and end times
        """
        try:
            # Decode base64 to binary
            audio_bytes = base64.b64decode(audio_data_b64)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Get word timestamps
                word_timestamps = self.get_word_timestamps(temp_file_path, text_content)
                return word_timestamps
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error processing base64 audio: {str(e)}")
            return []

# Global instance
force_alignment_service = ForceAlignmentService()

def run_force_alignment(db: Session, text_id: int) -> bool:
    """
    Run force alignment for a text using speech-only audio segments.
    
    Args:
        db: Database session
        text_id: ID of the text to run force alignment for
        
    Returns:
        True if alignment was successful, False otherwise
    """
    try:
        logger.info(f"Starting force alignment for text ID {text_id}")
        
        # Get text content
        db_text = crud.get_text(db, text_id)
        if not db_text:
            logger.error(f"Text with ID {text_id} not found")
            return False
        
        # Combine speech segments (no background music)
        speech_audio_path = combine_speech_segments(db, text_id)
        if not speech_audio_path:
            logger.error(f"Failed to combine speech segments for text ID {text_id}")
            return False
        
        try:
            # Run force alignment on speech-only audio
            word_timestamps = force_alignment_service.get_word_timestamps(speech_audio_path, db_text.content)
            
            if word_timestamps:
                # Store with current timestamp
                crud.update_text_word_timestamps(db, text_id, word_timestamps)
                logger.info(f"Successfully completed force alignment for text ID {text_id}, got {len(word_timestamps)} word timestamps")
                return True
            else:
                logger.warning(f"No word timestamps generated for text ID {text_id}")
                return False
                
        finally:
            # Clean up temporary speech audio file
            if os.path.exists(speech_audio_path):
                os.remove(speech_audio_path)
                logger.debug(f"Cleaned up temporary file: {speech_audio_path}")
                
    except Exception as e:
        logger.error(f"Error running force alignment for text ID {text_id}: {str(e)}")
        return False

def get_word_timestamps_for_text(combined_audio_path: str, text_content: str) -> List[Dict]:
    """
    Convenience function to get word timestamps for a text
    
    Args:
        combined_audio_path: Path to the combined audio file
        text_content: The complete text content
        
    Returns:
        List of word timestamps
    """
    return force_alignment_service.get_word_timestamps(combined_audio_path, text_content)

def get_word_timestamps_from_base64(audio_data_b64: str, text_content: str) -> List[Dict]:
    """
    Convenience function to get word timestamps from base64 audio
    
    Args:
        audio_data_b64: Base64 encoded audio data
        text_content: The complete text content
        
    Returns:
        List of word timestamps
    """
    return force_alignment_service.align_audio_from_base64(audio_data_b64, text_content) 