"""
Protocol defining the interface for audio generation services.
"""
from typing import Protocol, Dict, Any, Optional, BinaryIO, Union
from pathlib import Path

from src.narratix.core.domain.entities.text_content import TextContent
from src.narratix.core.domain.entities.voice import Voice
from src.narratix.core.domain.entities.narrative_element import NarrativeElement


class AudioGenerationService(Protocol):
    """
    Interface for audio generation operations.
    
    This service handles the generation of audio from text using
    specific voice profiles and adjustment parameters.
    """
    
    def generate_audio(
        self, 
        text: str, 
        voice: Voice, 
        params: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate audio for a text segment using the specified voice.
        
        Args:
            text: The text to convert to audio.
            voice: The voice profile to use for generation.
            params: Optional parameters for audio generation (e.g., speed,
                   pitch, emphasis).
                   
        Returns:
            Binary audio data.
        """
        ...
    
    def generate_narrative_audio(
        self, 
        narrative_element: NarrativeElement,
        params: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate audio for a narrative element.
        
        Args:
            narrative_element: The narrative element to convert to audio.
            params: Optional parameters for audio generation.
            
        Returns:
            Binary audio data.
        """
        ...
    
    def save_audio(
        self, 
        audio_data: bytes, 
        output_path: Union[str, Path], 
        format: str = "mp3"
    ) -> Path:
        """
        Save audio data to a file.
        
        Args:
            audio_data: The binary audio data to save.
            output_path: The path where to save the audio file.
            format: The audio format (default: "mp3").
            
        Returns:
            The path to the saved audio file.
        """
        ...
    
    def generate_full_narration(
        self, 
        text_content: TextContent,
        default_voice: Optional[Voice] = None,
        voice_mapping: Optional[Dict[str, Voice]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate audio for an entire text content with multiple voices.
        
        Args:
            text_content: The full text content to narrate.
            default_voice: The default voice for narrative segments.
            voice_mapping: A mapping from character names to voices.
            params: Optional parameters for audio generation.
            
        Returns:
            Binary audio data of the complete narration.
        """
        ...
    
    def adjust_audio_properties(
        self,
        audio_data: bytes,
        adjustments: Dict[str, Any]
    ) -> bytes:
        """
        Apply post-processing adjustments to audio data.
        
        Args:
            audio_data: The binary audio data to adjust.
            adjustments: A dictionary of adjustment parameters (e.g.,
                        volume, noise_reduction, equalization).
            
        Returns:
            Adjusted binary audio data.
        """
        ... 