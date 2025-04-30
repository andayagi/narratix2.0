"""Unit tests for the Voice entity."""
import pytest
from src.narratix.core.domain.entities import Voice


class TestVoice:
    """Test cases for the Voice class."""
    
    def test_init_with_required_args(self):
        """Test initialization with only required arguments."""
        voice_id = "voice-123"
        voice_name = "Test Voice"
        provider = "AWS"
        
        voice = Voice(voice_id, voice_name, provider)
        
        assert voice.voice_id == voice_id
        assert voice.voice_name == voice_name
        assert voice.provider == provider
        assert voice.gender == "Neutral"  # Default value
        assert voice.accent is None
        assert voice.voice_description is None
        assert voice.pitch == 0.0  # Default value
        
    def test_init_with_all_args(self):
        """Test initialization with all arguments."""
        voice_id = "voice-456"
        voice_name = "Complete Voice"
        provider = "Google"
        gender = "Female"
        accent = "British English"
        voice_description = "Professional newsreader voice"
        pitch = 0.5
        
        voice = Voice(
            voice_id, 
            voice_name, 
            provider, 
            gender, 
            accent, 
            voice_description, 
            pitch
        )
        
        assert voice.voice_id == voice_id
        assert voice.voice_name == voice_name
        assert voice.provider == provider
        assert voice.gender == gender
        assert voice.accent == accent
        assert voice.voice_description == voice_description
        assert voice.pitch == pitch
        
    def test_synthesize_placeholder(self):
        """Test the synthesize placeholder method."""
        voice = Voice("voice-789", "Placeholder Voice", "ElevenLabs")
        
        # Placeholder should return an empty bytes object
        result = voice.synthesize("Test text")
        assert isinstance(result, bytes)
        assert result == b''
        
    def test_str_representation(self):
        """Test string representation."""
        voice_name = "Test Voice"
        provider = "AWS"
        gender = "Male"
        
        voice = Voice("voice-id", voice_name, provider, gender)
        
        expected_str = f"Voice(name={voice_name}, provider={provider}, gender={gender})"
        assert str(voice) == expected_str 