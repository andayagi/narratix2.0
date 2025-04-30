import pytest
from uuid import uuid4

from narratix.core.domain.entities.character import Character as DomainCharacter
from narratix.infrastructure.database.repositories.sqlalchemy_character_repository import SQLAlchemyCharacterRepository

# Tests rely on the db_session fixture from tests/conftest.py

def test_add_and_get_character(db_session):
    """Test adding a Character entity and retrieving it by ID."""
    repo = SQLAlchemyCharacterRepository(db_session)
    
    # Create a domain entity
    name = "Test Character"
    description = "A character for integration test"
    domain_entity = DomainCharacter(name=name, description=description)
    
    # Add to repository
    added_entity = repo.create(domain_entity)
    
    # Retrieve by ID
    retrieved_entity = repo.get_by_id(added_entity.id)
    
    assert retrieved_entity is not None
    assert retrieved_entity.id == added_entity.id
    assert retrieved_entity.name == name
    assert retrieved_entity.description == description

def test_get_non_existent_character(db_session):
    """Test retrieving a non-existent Character returns None."""
    repo = SQLAlchemyCharacterRepository(db_session)
    
    non_existent_id = uuid4()  # Generate a random UUID
    retrieved_entity = repo.get_by_id(non_existent_id)
    
    assert retrieved_entity is None

def test_list_characters(db_session):
    """Test listing Character entities."""
    repo = SQLAlchemyCharacterRepository(db_session)
    
    # Add a couple of entities
    entity1 = DomainCharacter(name="First Character", description="Description 1")
    entity2 = DomainCharacter(name="Second Character", description="Description 2")
    repo.create(entity1)
    repo.create(entity2)
    
    all_entities = repo.list()
    
    assert len(all_entities) >= 2
    names = {e.name for e in all_entities}
    assert "First Character" in names
    assert "Second Character" in names

def test_get_by_name(db_session):
    """Test retrieving Characters by name."""
    repo = SQLAlchemyCharacterRepository(db_session)
    
    # Add test entities
    entity1 = DomainCharacter(name="John Smith", description="Description 1")
    entity2 = DomainCharacter(name="Jane Smith", description="Description 2")
    entity3 = DomainCharacter(name="Bob Johnson", description="Description 3")
    
    repo.create(entity1)
    repo.create(entity2)
    repo.create(entity3)
    
    # Search by partial name match
    smith_chars = repo.get_by_name("Smith")
    
    assert len(smith_chars) == 2
    smith_names = {e.name for e in smith_chars}
    assert "John Smith" in smith_names
    assert "Jane Smith" in smith_names
    assert "Bob Johnson" not in smith_names

def test_update_character(db_session):
    """Test updating a Character entity."""
    repo = SQLAlchemyCharacterRepository(db_session)
    
    # Create and add a character
    character = DomainCharacter(name="Original Name", description="Original description")
    added_character = repo.create(character)
    
    # Update the character
    added_character.name = "Updated Name"
    added_character.description = "Updated description"
    
    updated_character = repo.update(added_character)
    
    # Retrieve to verify update
    retrieved_character = repo.get_by_id(added_character.id)
    
    assert retrieved_character.name == "Updated Name"
    assert retrieved_character.description == "Updated description"

def test_delete_character(db_session):
    """Test deleting a Character entity."""
    repo = SQLAlchemyCharacterRepository(db_session)
    
    # Create and add a character
    character = DomainCharacter(name="To Delete", description="Will be deleted")
    added_character = repo.create(character)
    
    # Verify it exists
    assert repo.get_by_id(added_character.id) is not None
    
    # Delete it
    success = repo.delete(added_character.id)
    
    # Verify deletion
    assert success is True
    assert repo.get_by_id(added_character.id) is None

def test_get_by_voice_id(db_session):
    """Test retrieving Characters by voice ID."""
    repo = SQLAlchemyCharacterRepository(db_session)
    
    # Create a random voice ID
    voice_id = uuid4()
    
    # Create characters with different voice IDs
    character1 = DomainCharacter(name="Character with voice 1", description="Description")
    character1.voice_id = voice_id
    
    character2 = DomainCharacter(name="Character with voice 1 too", description="Description")
    character2.voice_id = voice_id
    
    character3 = DomainCharacter(name="Character with different voice", description="Description")
    character3.voice_id = uuid4()  # Different voice ID
    
    # Add characters to repository
    repo.create(character1)
    repo.create(character2)
    repo.create(character3)
    
    # Get characters by voice ID
    characters = repo.get_by_voice_id(voice_id)
    
    # Verify results
    assert len(characters) == 2
    character_names = {c.name for c in characters}
    assert "Character with voice 1" in character_names
    assert "Character with voice 1 too" in character_names
    assert "Character with different voice" not in character_names 