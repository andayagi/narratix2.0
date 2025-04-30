"""Unit tests for the NarrativeElement entity."""
import pytest
from uuid import UUID
from src.narratix.core.domain.entities import NarrativeElement, Character, Voice


class TestNarrativeElement:
    """Test cases for the NarrativeElement class."""
    
    @pytest.fixture
    def character(self):
        """Fixture providing a Character instance for testing."""
        return Character("Test Character")
    
    def test_init_with_required_args(self, character):
        """Test initialization with required arguments only."""
        text = "This is a test narrative segment."
        start = 0
        end = len(text)
        
        element = NarrativeElement(text, character, start, end)
        
        assert element.text_segment == text
        assert element.character is character
        assert element.start_offset == start
        assert element.end_offset == end
        assert element.element_type == "narration"  # Default
        assert isinstance(element.element_id, UUID)
        assert element.acting_instructions is None
        assert element.speed == 1.0  # Default
        assert element.trailing_silence == 0.0  # Default
        
    def test_init_with_custom_args(self, character):
        """Test initialization with custom arguments."""
        text = "Hello, world!"
        start = 10
        end = 23
        element_type = "dialogue"
        element_id = "test-id-123"
        instructions = "speak excitedly"
        speed = 1.5
        silence = 0.5
        
        element = NarrativeElement(
            text, 
            character, 
            start, 
            end, 
            element_type, 
            element_id, 
            instructions, 
            speed, 
            silence
        )
        
        assert element.text_segment == text
        assert element.character is character
        assert element.start_offset == start
        assert element.end_offset == end
        assert element.element_type == element_type
        assert element.element_id == element_id
        assert element.acting_instructions == instructions
        assert element.speed == speed
        assert element.trailing_silence == silence
        
    def test_invalid_element_type(self, character):
        """Test initialization with invalid element type."""
        with pytest.raises(ValueError, match="Invalid element_type"):
            NarrativeElement("text", character, 0, 4, "invalid_type")
            
    def test_invalid_offsets(self, character):
        """Test initialization with invalid offset values."""
        # Test negative start offset
        with pytest.raises(ValueError, match="Invalid offset values"):
            NarrativeElement("text", character, -1, 4)
            
        # Test end offset less than start offset
        with pytest.raises(ValueError, match="Invalid offset values"):
            NarrativeElement("text", character, 10, 5)
            
    def test_invalid_character_type(self):
        """Test initialization with invalid character type."""
        with pytest.raises(TypeError, match="Expected a Character object"):
            NarrativeElement("text", "not-a-character", 0, 4)
            
    def test_get_assigned_voice(self, character):
        """Test getting the assigned voice from the character."""
        voice = Voice("voice-id", "Test Voice", "AWS")
        character.assign_voice(voice)
        
        element = NarrativeElement("text", character, 0, 4)
        
        assert element.get_assigned_voice() is voice
        
    def test_str_representation(self, character):
        """Test string representation."""
        text = "Test segment"
        element = NarrativeElement(text, character, 0, len(text))
        
        expected_str = f"NarrativeElement(id={element.element_id}, type=narration, character={character.name}, length={len(text)})"
        assert str(element) == expected_str 