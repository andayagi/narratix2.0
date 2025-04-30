"""
Tests for the AudioGenerationService protocol.
"""
import unittest
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Union, Protocol, runtime_checkable

from src.narratix.core.domain.entities.voice import Voice
from src.narratix.core.domain.entities.text_content import TextContent
from src.narratix.core.domain.entities.character import Character
from src.narratix.core.domain.entities.narrative_element import NarrativeElement
from src.narratix.core.domain.services.audio_generation_service import AudioGenerationService


class MockAudioGenerationService:
    """Mock implementation of AudioGenerationService for testing."""
    
    def generate_audio(
        self, 
        text: str, 
        voice: Voice, 
        params: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate mock audio data."""
        # For testing purposes, just return some bytes
        return f"Mock audio for '{text}' using voice {voice.voice_name}".encode()
    
    def generate_narrative_audio(
        self, 
        narrative_element: NarrativeElement,
        params: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate mock audio for a narrative element."""
        return f"Mock audio for {narrative_element.element_type} element".encode()
    
    def save_audio(
        self, 
        audio_data: bytes, 
        output_path: Union[str, Path], 
        format: str = "mp3"
    ) -> Path:
        """Mock saving audio to a file."""
        path = Path(output_path)
        # Just return the path for testing
        return path
    
    def generate_full_narration(
        self, 
        text_content: TextContent,
        default_voice: Optional[Voice] = None,
        voice_mapping: Optional[Dict[str, Voice]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate mock audio for a full text content."""
        return f"Mock full narration for text content".encode()
    
    def adjust_audio_properties(
        self,
        audio_data: bytes,
        adjustments: Dict[str, Any]
    ) -> bytes:
        """Apply mock adjustments to audio data."""
        # Just return the original data for testing
        return audio_data


class TestAudioGenerationService(unittest.TestCase):
    """Tests for the AudioGenerationService protocol."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = MockAudioGenerationService()
        
        # Create a test voice
        self.test_voice = Voice(
            voice_id="voice-1",
            voice_name="Test Voice",
            provider="AWS",
            gender="Female",
            accent="US English"
        )
        
        # Create a test text content
        self.sample_text_content = TextContent(
            content="This is a test narrative content.",
            language="en",
            metadata={"title": "Test Story"}
        )
        
        # Create a test character
        self.test_character = Character(
            name="Narrator",
            description="Narrative voice"
        )
        
        # Create a test narrative element
        self.narrative_element = NarrativeElement(
            text_segment="Once upon a time...",
            character=self.test_character,
            start_offset=0,
            end_offset=18,
            element_type="narration"
        )
    
    def test_protocol_conformance(self):
        """Test that our mock correctly implements the protocol."""
        # Since Protocol classes don't have a direct way to check conformance in runtime,
        # we'll just check that the service has all the required methods
        self.assertTrue(hasattr(self.mock_service, "generate_audio"))
        self.assertTrue(hasattr(self.mock_service, "generate_narrative_audio"))
        self.assertTrue(hasattr(self.mock_service, "save_audio"))
        self.assertTrue(hasattr(self.mock_service, "generate_full_narration"))
        self.assertTrue(hasattr(self.mock_service, "adjust_audio_properties"))
    
    def test_generate_audio(self):
        """Test the generate_audio method."""
        audio_data = self.mock_service.generate_audio(
            "Hello world", self.test_voice
        )
        self.assertIsInstance(audio_data, bytes)
        self.assertTrue(len(audio_data) > 0)
    
    def test_generate_narrative_audio(self):
        """Test the generate_narrative_audio method."""
        audio_data = self.mock_service.generate_narrative_audio(
            self.narrative_element
        )
        self.assertIsInstance(audio_data, bytes)
        self.assertTrue(len(audio_data) > 0)
    
    def test_save_audio(self):
        """Test the save_audio method."""
        # Create a test file path
        with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
            test_path = Path(tmp.name)
            
        audio_data = b"Test audio data"
        output_path = self.mock_service.save_audio(
            audio_data, test_path, "mp3"
        )
        
        self.assertIsInstance(output_path, Path)
        self.assertEqual(output_path, test_path)
    
    def test_generate_full_narration(self):
        """Test the generate_full_narration method."""
        voice_mapping = {
            "character1": self.test_voice
        }
        
        audio_data = self.mock_service.generate_full_narration(
            self.sample_text_content,
            default_voice=self.test_voice,
            voice_mapping=voice_mapping
        )
        
        self.assertIsInstance(audio_data, bytes)
        self.assertTrue(len(audio_data) > 0)
    
    def test_adjust_audio_properties(self):
        """Test the adjust_audio_properties method."""
        original_data = b"Original audio data"
        adjustments = {
            "volume": 1.5,
            "noise_reduction": True
        }
        
        adjusted_data = self.mock_service.adjust_audio_properties(
            original_data, adjustments
        )
        
        self.assertIsInstance(adjusted_data, bytes)
        # In our mock, the data should remain unchanged
        self.assertEqual(adjusted_data, original_data)


if __name__ == "__main__":
    unittest.main() 