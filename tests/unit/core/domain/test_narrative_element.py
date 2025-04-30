import pytest
from uuid import UUID
from narratix.core.domain.entities.narrative_element import NarrativeElement
from narratix.core.domain.entities.character import Character

@pytest.fixture
def mock_character():
    """Fixture to create a mock Character instance."""
    return Character(name="Narrator")

def test_narrative_element_initialization(mock_character):
    """Test basic initialization of NarrativeElement."""
    text = "Once upon a time..."
    start = 0
    end = 19
    element_type = "narration"
    
    element = NarrativeElement(
        text_segment=text,
        character=mock_character,
        start_offset=start,
        end_offset=end,
        element_type=element_type
    )
    
    assert isinstance(element.element_id, UUID)
    assert element.text_segment == text
    assert element.character == mock_character
    assert element.start_offset == start
    assert element.end_offset == end
    assert element.element_type == element_type
    assert element.acting_instructions is None
    assert element.speed == 1.0
    assert element.trailing_silence == 0.0

def test_narrative_element_dialogue_initialization(mock_character):
    """Test initialization with specific dialogue type and attributes."""
    text = "\"Hello!\" she exclaimed."
    start = 20
    end = 40
    element_type = "dialogue"
    instructions = "Excitedly"
    speed = 1.2
    silence = 0.5
    
    element = NarrativeElement(
        text_segment=text,
        character=mock_character,
        start_offset=start,
        end_offset=end,
        element_type=element_type,
        acting_instructions=instructions,
        speed=speed,
        trailing_silence=silence
    )
    
    assert element.element_type == element_type
    assert element.acting_instructions == instructions
    assert element.speed == speed
    assert element.trailing_silence == silence

def test_narrative_element_invalid_type_raises_error(mock_character):
    """Test that initializing with an invalid element type raises ValueError."""
    with pytest.raises(ValueError, match="Invalid element_type"):
        NarrativeElement(
            text_segment="Test",
            character=mock_character,
            start_offset=0,
            end_offset=4,
            element_type="invalid_type"
        )

def test_narrative_element_invalid_offset_raises_error(mock_character):
    """Test that initializing with invalid offsets raises ValueError."""
    with pytest.raises(ValueError, match="Invalid offset values"):
        NarrativeElement(
            text_segment="Test",
            character=mock_character,
            start_offset=5, # start > end
            end_offset=4,
            element_type="narration"
        )
    with pytest.raises(ValueError, match="Invalid offset values"):
        NarrativeElement(
            text_segment="Test",
            character=mock_character,
            start_offset=-1, # start < 0
            end_offset=4,
            element_type="narration"
        ) 