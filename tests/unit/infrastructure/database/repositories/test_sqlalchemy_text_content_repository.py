"""Tests for SQLAlchemyTextContentRepository."""
import uuid
import pytest

from narratix.infrastructure.database.repositories.sqlalchemy_text_content_repository import SQLAlchemyTextContentRepository
from narratix.core.domain.entities.text_content import TextContent


class TestSQLAlchemyTextContentRepository:
    """Test suite for SQLAlchemyTextContentRepository."""
    
    def test_create(self, db_session, sample_text_content):
        """Test creating a TextContent entity."""
        # Arrange
        repo = SQLAlchemyTextContentRepository(db_session)
        
        # Act
        result = repo.create(sample_text_content)
        
        # Assert
        assert result is not None
        assert isinstance(result, TextContent)
        assert result.content == sample_text_content.content
        assert result.language == sample_text_content.language
        assert result.metadata == sample_text_content.metadata
        assert hasattr(result, 'id')
        assert result.id is not None
        
    def test_get_by_id(self, db_session, sample_text_content):
        """Test retrieving a TextContent entity by ID."""
        # Arrange
        repo = SQLAlchemyTextContentRepository(db_session)
        created = repo.create(sample_text_content)
        
        # Act
        result = repo.get_by_id(created.id)
        
        # Assert
        assert result is not None
        assert result.id == created.id
        assert result.content == created.content
        
    def test_get_by_id_not_found(self, db_session):
        """Test retrieving a non-existent TextContent entity."""
        # Arrange
        repo = SQLAlchemyTextContentRepository(db_session)
        
        # Act
        result = repo.get_by_id(uuid.uuid4())
        
        # Assert
        assert result is None
        
    def test_list(self, db_session, sample_text_content):
        """Test listing TextContent entities."""
        # Arrange
        repo = SQLAlchemyTextContentRepository(db_session)
        created = repo.create(sample_text_content)
        
        # Create another entity with different language
        another_content = TextContent(
            content="This is another test content.",
            language="es",
            metadata={"source": "test"}
        )
        repo.create(another_content)
        
        # Act
        all_results = repo.list()
        en_results = repo.list(language="en")
        es_results = repo.list(language="es")
        
        # Assert
        assert len(all_results) == 2
        assert len(en_results) == 1
        assert len(es_results) == 1
        assert en_results[0].language == "en"
        assert es_results[0].language == "es"
        
    def test_update(self, db_session, sample_text_content):
        """Test updating a TextContent entity."""
        # Arrange
        repo = SQLAlchemyTextContentRepository(db_session)
        created = repo.create(sample_text_content)
        
        # Modify the entity
        created.content = "Updated content"
        created.metadata = {"source": "updated"}
        
        # Act
        updated = repo.update(created)
        
        # Assert
        assert updated.content == "Updated content"
        assert updated.metadata == {"source": "updated"}
        
        # Verify by getting from repository
        fetched = repo.get_by_id(created.id)
        assert fetched.content == "Updated content"
        assert fetched.metadata == {"source": "updated"}
        
    def test_delete(self, db_session, sample_text_content):
        """Test deleting a TextContent entity."""
        # Arrange
        repo = SQLAlchemyTextContentRepository(db_session)
        created = repo.create(sample_text_content)
        
        # Act
        result = repo.delete(created.id)
        
        # Assert
        assert result is True
        assert repo.get_by_id(created.id) is None
        
    def test_delete_not_found(self, db_session):
        """Test deleting a non-existent TextContent entity."""
        # Arrange
        repo = SQLAlchemyTextContentRepository(db_session)
        
        # Act
        result = repo.delete(uuid.uuid4())
        
        # Assert
        assert result is False
        
    def test_search_by_content(self, db_session, sample_text_content):
        """Test searching TextContent by content text."""
        # Arrange
        repo = SQLAlchemyTextContentRepository(db_session)
        repo.create(sample_text_content)
        
        # Create another entity with different content
        another_content = TextContent(
            content="This is about programming and coding.",
            language="en"
        )
        repo.create(another_content)
        
        # Act
        results_sample = repo.search_by_content("sample")
        results_programming = repo.search_by_content("programming")
        results_nonexistent = repo.search_by_content("nonexistent")
        
        # Assert
        assert len(results_sample) == 1
        assert len(results_programming) == 1
        assert len(results_nonexistent) == 0
        assert results_sample[0].content == sample_text_content.content
        assert results_programming[0].content == another_content.content
        
    def test_get_by_language(self, db_session, sample_text_content):
        """Test retrieving TextContent by language."""
        # Arrange
        repo = SQLAlchemyTextContentRepository(db_session)
        repo.create(sample_text_content)  # English
        
        # Create another entity with Spanish language
        spanish_content = TextContent(
            content="Este es un contenido de prueba.",
            language="es"
        )
        repo.create(spanish_content)
        
        # Act
        results_en = repo.get_by_language("en")
        results_es = repo.get_by_language("es")
        results_fr = repo.get_by_language("fr")
        
        # Assert
        assert len(results_en) == 1
        assert len(results_es) == 1
        assert len(results_fr) == 0
        assert results_en[0].language == "en"
        assert results_es[0].language == "es" 