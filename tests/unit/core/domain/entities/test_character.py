"""Unit tests for the Character entity."""
import pytest
from src.narratix.core.domain.entities import Character, Voice


class TestCharacter:
    """Test cases for the Character class."""
    
    def test_init_with_name_only(self):
        """Test initialization with name only."""
        name = "Narrator"
        character = Character(name)
        
        assert character.name == name
        assert character.description is None
        assert character.voice is None
        
    def test_init_with_description(self):
        """Test initialization with name and description."""
        name = "Alice"
        description = "Main protagonist, young female voice"
        character = Character(name, description)
        
        assert character.name == name
        assert character.description == description
        assert character.voice is None
        
    def test_assign_voice(self):
        """Test assigning a voice to the character."""
        character = Character("Bob")
        voice = Voice("voice-id-123", "Male Voice", "AWS")
        
        character.assign_voice(voice)
        
        assert character.voice is voice
        
    def test_assign_invalid_voice(self):
        """Test assigning an invalid voice object."""
        character = Character("Charlie")
        
        with pytest.raises(TypeError, match="Expected a Voice object"):
            character.assign_voice("not-a-voice-object")
            
    def test_str_representation_no_voice(self):
        """Test string representation without an assigned voice."""
        name = "David"
        character = Character(name)
        
        expected_str = f"Character(name={name}, no voice assigned)"
        assert str(character) == expected_str
        
    def test_str_representation_with_voice(self):
        """Test string representation with an assigned voice."""
        name = "Eve"
        character = Character(name)
        voice_name = "Female Voice"
        voice = Voice("voice-id-456", voice_name, "Google")
        
        character.assign_voice(voice)
        
        expected_str = f"Character(name={name}, voice={voice_name})"
        assert str(character) == expected_str 