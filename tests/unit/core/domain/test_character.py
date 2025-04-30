import pytest
from narratix.core.domain.entities.character import Character

def test_character_initialization():
    """Test basic initialization of Character."""
    name = "Alice"
    description = "Curious girl"
    
    character = Character(name=name, description=description)
    
    assert character.name == name
    assert character.description == description
    assert character.voice is None

def test_character_initialization_minimal():
    """Test initialization with only the required name."""
    name = "Narrator"
    
    character = Character(name=name)
    
    assert character.name == name
    assert character.description is None
    assert character.voice is None 