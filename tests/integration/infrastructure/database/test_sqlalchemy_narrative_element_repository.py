import pytest
from uuid import uuid4, UUID

from narratix.core.domain.entities.narrative_element import NarrativeElement
from narratix.core.domain.entities.character import Character
from narratix.infrastructure.database.repositories.sqlalchemy_narrative_element_repository import SQLAlchemyNarrativeElementRepository

# Tests rely on the db_session fixture from tests/conftest.py

def test_add_and_get_narrative_element(db_session):
    """Test adding a NarrativeElement entity and retrieving it by ID."""
    repo = SQLAlchemyNarrativeElementRepository(db_session)
    
    # Create a character
    character = Character(name="Test Character")
    
    # Create a domain entity
    element_type = "dialogue"
    
    domain_entity = NarrativeElement(
        text_segment="Hello, world!",
        start_offset=0,
        end_offset=13,
        element_type=element_type,
        character=character
    )
    
    # Add text_content_id attribute directly
    domain_entity.text_content_id = uuid4()
    
    # Add to repository
    added_entity = repo.create(domain_entity)
    
    # Retrieve by ID
    retrieved_entity = repo.get_by_id(added_entity.id)
    
    assert retrieved_entity is not None
    assert retrieved_entity.id == added_entity.id
    assert retrieved_entity.element_type == element_type
    assert retrieved_entity.text_content_id == domain_entity.text_content_id
    assert retrieved_entity.text_segment == "Hello, world!"

def test_get_non_existent_narrative_element(db_session):
    """Test retrieving a non-existent NarrativeElement returns None."""
    repo = SQLAlchemyNarrativeElementRepository(db_session)
    
    non_existent_id = uuid4()  # Generate a random UUID
    retrieved_entity = repo.get_by_id(non_existent_id)
    
    assert retrieved_entity is None

def test_list_narrative_elements(db_session):
    """Test listing NarrativeElement entities."""
    repo = SQLAlchemyNarrativeElementRepository(db_session)
    
    # Create characters
    character1 = Character(name="Narrator")
    character2 = Character(name="Alice")
    
    # Add a couple of entities
    entity1 = NarrativeElement(
        text_segment="This is narration text.",
        start_offset=0,
        end_offset=24,
        element_type="narration",
        character=character1
    )
    entity2 = NarrativeElement(
        text_segment="This is dialogue text.",
        start_offset=0,
        end_offset=23, 
        element_type="dialogue",
        character=character2
    )
    
    # Add text_content_id attributes directly
    entity1.text_content_id = uuid4()
    entity2.text_content_id = uuid4()
    
    # Add character_id to entity2 directly
    entity2.character_id = uuid4()
    
    repo.create(entity1)
    repo.create(entity2)
    
    all_entities = repo.list()
    
    assert len(all_entities) >= 2
    element_types = {e.element_type for e in all_entities}
    assert "narration" in element_types
    assert "dialogue" in element_types

def test_get_by_element_type(db_session):
    """Test retrieving NarrativeElements by element_type."""
    repo = SQLAlchemyNarrativeElementRepository(db_session)
    
    # Create characters
    character1 = Character(name="Narrator")
    character2 = Character(name="Alice")
    
    # Add test entities with different types
    entity1 = NarrativeElement(
        text_segment="Narration 1",
        start_offset=0,
        end_offset=11,
        element_type="narration",
        character=character1
    )
    entity2 = NarrativeElement(
        text_segment="Dialogue 1",
        start_offset=0,
        end_offset=10,
        element_type="dialogue",
        character=character2
    )
    entity3 = NarrativeElement(
        text_segment="Narration 2",
        start_offset=0,
        end_offset=11,
        element_type="narration",
        character=character1
    )
    
    # Add text_content_id attributes directly
    entity1.text_content_id = uuid4()
    entity2.text_content_id = uuid4()
    entity3.text_content_id = uuid4()
    
    # Add character_id to entity2 directly
    entity2.character_id = uuid4()
    
    repo.create(entity1)
    repo.create(entity2)
    repo.create(entity3)
    
    # Get elements by type
    narration_elements = repo.get_by_element_type("narration")
    
    assert len(narration_elements) == 2
    for element in narration_elements:
        assert element.element_type == "narration"

def test_get_by_text_content_id(db_session):
    """Test retrieving NarrativeElements by text_content_id."""
    repo = SQLAlchemyNarrativeElementRepository(db_session)
    
    text_content_id1 = uuid4()
    text_content_id2 = uuid4()
    
    # Create characters
    character1 = Character(name="Narrator")
    character2 = Character(name="Alice")
    
    # Add test entities with different text_content_ids
    entity1 = NarrativeElement(
        text_segment="Element 1 for Text 1",
        start_offset=0,
        end_offset=20,
        element_type="narration",
        character=character1
    )
    entity2 = NarrativeElement(
        text_segment="Element 2 for Text 1",
        start_offset=21,
        end_offset=40,
        element_type="dialogue",
        character=character2
    )
    entity3 = NarrativeElement(
        text_segment="Element 1 for Text 2",
        start_offset=0,
        end_offset=20,
        element_type="narration",
        character=character1
    )
    
    # Set text_content_id attributes directly
    entity1.text_content_id = text_content_id1
    entity2.text_content_id = text_content_id1
    entity3.text_content_id = text_content_id2
    
    repo.create(entity1)
    repo.create(entity2)
    repo.create(entity3)
    
    # Get elements by text_content_id
    text1_elements = repo.get_by_text_content_id(text_content_id1)
    
    assert len(text1_elements) == 2
    for element in text1_elements:
        assert element.text_content_id == text_content_id1

def test_get_by_character_id(db_session):
    """Test retrieving NarrativeElements by character_id."""
    repo = SQLAlchemyNarrativeElementRepository(db_session)
    
    character_id1 = uuid4()
    character_id2 = uuid4()
    
    # Create characters
    character1 = Character(name="Character 1")
    character2 = Character(name="Character 2")
    
    # Add test entities with different character_ids
    entity1 = NarrativeElement(
        text_segment="Character 1 speaks first",
        start_offset=0,
        end_offset=24,
        element_type="dialogue",
        character=character1
    )
    entity2 = NarrativeElement(
        text_segment="Character 1 speaks again",
        start_offset=25,
        end_offset=49,
        element_type="dialogue",
        character=character1
    )
    entity3 = NarrativeElement(
        text_segment="Character 2 speaks",
        start_offset=50,
        end_offset=67,
        element_type="dialogue",
        character=character2
    )
    
    # Set text_content_id and character_id attributes directly
    entity1.text_content_id = uuid4()
    entity2.text_content_id = uuid4()
    entity3.text_content_id = uuid4()
    
    entity1.character_id = character_id1
    entity2.character_id = character_id1
    entity3.character_id = character_id2
    
    repo.create(entity1)
    repo.create(entity2)
    repo.create(entity3)
    
    # Get elements by character_id
    character1_elements = repo.get_by_character_id(character_id1)
    
    assert len(character1_elements) == 2
    for element in character1_elements:
        assert element.character_id == character_id1

def test_update_narrative_element(db_session):
    """Test updating a NarrativeElement entity."""
    repo = SQLAlchemyNarrativeElementRepository(db_session)
    
    # Create a character
    character = Character(name="Narrator")
    
    # Create and add a narrative element
    element = NarrativeElement(
        text_segment="Original text",
        start_offset=0,
        end_offset=13,
        element_type="narration",
        character=character
    )
    
    # Set text_content_id attribute directly
    element.text_content_id = uuid4()
    
    added_element = repo.create(element)
    
    # Update the element
    added_element.text_segment = "Updated text"
    added_element.end_offset = 12
    added_element.element_type = "dialogue"
    added_element.character_id = uuid4()
    
    updated_element = repo.update(added_element)
    
    # Retrieve to verify update
    retrieved_element = repo.get_by_id(added_element.id)
    
    assert retrieved_element.text_segment == "Updated text"
    assert retrieved_element.end_offset == 12
    assert retrieved_element.element_type == "dialogue"
    assert retrieved_element.character_id == added_element.character_id

def test_delete_narrative_element(db_session):
    """Test deleting a NarrativeElement entity."""
    repo = SQLAlchemyNarrativeElementRepository(db_session)
    
    # Create a character
    character = Character(name="Narrator")
    
    # Create and add a narrative element
    element = NarrativeElement(
        text_segment="Text to delete",
        start_offset=0,
        end_offset=14,
        element_type="narration",
        character=character
    )
    
    # Set text_content_id attribute directly
    element.text_content_id = uuid4()
    
    added_element = repo.create(element)
    
    # Verify it exists
    assert repo.get_by_id(added_element.id) is not None
    
    # Delete it
    success = repo.delete(added_element.id)
    
    # Verify deletion
    assert success is True
    assert repo.get_by_id(added_element.id) is None 