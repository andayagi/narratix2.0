from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pathlib import Path
import asyncio

class AudioGeneratorInterface(ABC):
    """Interface for audio generation capabilities."""
    
    @abstractmethod
    async def generate_audio(self, text: str, voice_id: str, 
                           speed: float = 1.0, 
                           trailing_silence: float = 0.0) -> Optional[bytes]:
        """Generate audio for a single piece of text.
        
        Args:
            text: Text to convert to speech
            voice_id: ID of the voice to use
            speed: Speech speed multiplier
            trailing_silence: Seconds of silence to add at the end
            
        Returns:
            Audio data as bytes or None if generation failed
        """
        pass
    
    @abstractmethod
    async def generate_audio_segments(self, 
                                   narrative_elements: List[Dict[str, Any]],
                                   story_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generate audio for multiple narrative elements.
        
        Args:
            narrative_elements: List of dictionaries containing:
                - text: Text to convert to speech
                - role: Character/voice name
                - segment_id: Identifier for the segment
                - is_narrator: Whether this is narration
            story_id: Identifier for the story
            
        Returns:
            List of dictionaries with text, voice, character, and output_filepath
        """
        pass
    
    @abstractmethod
    async def combine_audio_segments(self, 
                                   audio_segments: List[Dict[str, Any]],
                                   output_filename: str) -> Optional[str]:
        """Combine audio segments into a single audio file.
        
        Args:
            audio_segments: List of dictionaries with output_filepath
            output_filename: Name for the output file
            
        Returns:
            Path to the combined audio file or None if combination failed
        """
        pass 