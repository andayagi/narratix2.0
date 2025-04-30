import pytest
from uuid import uuid4

from narratix.core.domain.entities.text_content import TextContent as DomainTextContent
from narratix.infrastructure.database.repositories.sqlalchemy_text_content_repository import SQLAlchemyTextContentRepository

# Tests rely on the db_session fixture from tests/conftest.py

def test_add_and_get_text_content(db_session):
    """Test adding a TextContent entity and retrieving it by ID."""
    repo = SQLAlchemyTextContentRepository(db_session)
    
    # Create a domain entity
    content = "Test content for integration test."
    language = "en-test"
    metadata = {"source": "integration_test"}
    domain_entity = DomainTextContent(content=content, language=language, metadata=metadata)
    
    # Add to repository
    added_entity = repo.create(domain_entity)
    
    # Retrieve by ID
    retrieved_entity = repo.get_by_id(added_entity.id)
    
    assert retrieved_entity is not None
    assert retrieved_entity.id == added_entity.id
    assert retrieved_entity.content == content
    assert retrieved_entity.language == language
    assert retrieved_entity.metadata == metadata

def test_get_non_existent_text_content(db_session):
    """Test retrieving a non-existent TextContent returns None."""
    repo = SQLAlchemyTextContentRepository(db_session)
    
    non_existent_id = uuid4() # Generate a random UUID
    retrieved_entity = repo.get_by_id(non_existent_id)
    
    assert retrieved_entity is None

def test_list_text_contents(db_session):
    """Test listing TextContent entities."""
    repo = SQLAlchemyTextContentRepository(db_session)
    
    # Add a couple of entities
    entity1 = DomainTextContent(content="First content")
    entity2 = DomainTextContent(content="Second content", language="fr")
    repo.create(entity1)
    repo.create(entity2)
    
    all_entities = repo.list()
    
    assert len(all_entities) == 2
    contents = {e.content for e in all_entities}
    assert "First content" in contents
    assert "Second content" in contents

def test_update_text_content(db_session):
    """Test updating a TextContent entity."""
    repo = SQLAlchemyTextContentRepository(db_session)
    
    # Create initial entity
    initial_content = "Initial content"
    entity = DomainTextContent(content=initial_content, language="en")
    created_entity = repo.create(entity)
    
    # Update the entity
    created_entity.content = "Updated content"
    created_entity.language = "fr"
    created_entity.metadata = {"updated": True}
    
    updated_entity = repo.update(created_entity)
    
    # Verify the update
    retrieved_entity = repo.get_by_id(created_entity.id)
    assert retrieved_entity.content == "Updated content"
    assert retrieved_entity.language == "fr"
    assert retrieved_entity.metadata == {"updated": True}

def test_delete_text_content(db_session):
    """Test deleting a TextContent entity."""
    repo = SQLAlchemyTextContentRepository(db_session)
    
    # Create entity
    entity = DomainTextContent(content="Content to delete")
    created_entity = repo.create(entity)
    
    # Verify it exists
    assert repo.get_by_id(created_entity.id) is not None
    
    # Delete it
    repo.delete(created_entity.id)
    
    # Verify it's gone
    assert repo.get_by_id(created_entity.id) is None

def test_search_by_content(db_session):
    """Test searching TextContent entities by content."""
    repo = SQLAlchemyTextContentRepository(db_session)
    
    # Create entities with different content
    repo.create(DomainTextContent(content="This is about apples"))
    repo.create(DomainTextContent(content="This is about bananas"))
    repo.create(DomainTextContent(content="This is about apples and oranges"))
    
    # Search for "apple"
    results = repo.search_by_content("apple")
    
    assert len(results) == 2
    for entity in results:
        assert "apple" in entity.content.lower()

def test_get_by_language(db_session):
    """Test retrieving TextContent entities by language."""
    repo = SQLAlchemyTextContentRepository(db_session)
    
    # Create entities with different languages
    repo.create(DomainTextContent(content="English content", language="en"))
    repo.create(DomainTextContent(content="French content", language="fr"))
    repo.create(DomainTextContent(content="More English content", language="en"))
    
    # Get entities by language
    en_results = repo.get_by_language("en")
    fr_results = repo.get_by_language("fr")
    
    assert len(en_results) == 2
    assert len(fr_results) == 1
    
    for entity in en_results:
        assert entity.language == "en"
    
    for entity in fr_results:
        assert entity.language == "fr" 