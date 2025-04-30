"""Tests for SQLAlchemyCharacterRepository."""
import uuid
import pytest

from narratix.infrastructure.database.repositories.sqlalchemy_character_repository import SQLAlchemyCharacterRepository
from narratix.core.domain.entities.character import Character


class TestSQLAlchemyCharacterRepository:
    """Test suite for SQLAlchemyCharacterRepository."""
    
    def test_create(self, db_session, sample_character):
        """Test creating a Character entity."""
        # Arrange
        repo = SQLAlchemyCharacterRepository(db_session)
        
        # Act
        result = repo.create(sample_character)
        
        # Assert
        assert result is not None
        assert isinstance(result, Character)
        assert result.name == sample_character.name
        assert result.description == sample_character.description
        assert hasattr(result, 'id')
        assert result.id is not None
        
    def test_get_by_id(self, db_session, sample_character):
        """Test retrieving a Character entity by ID."""
        # Arrange
        repo = SQLAlchemyCharacterRepository(db_session)
        created = repo.create(sample_character)
        
        # Act
        result = repo.get_by_id(created.id)
        
        # Assert
        assert result is not None
        assert result.id == created.id
        assert result.name == created.name
        
    def test_get_by_id_not_found(self, db_session):
        """Test retrieving a non-existent Character entity."""
        # Arrange
        repo = SQLAlchemyCharacterRepository(db_session)
        
        # Act
        result = repo.get_by_id(uuid.uuid4())
        
        # Assert
        assert result is None
        
    def test_list(self, db_session, sample_character):
        """Test listing Character entities."""
        # Arrange
        repo = SQLAlchemyCharacterRepository(db_session)
        created = repo.create(sample_character)
        
        # Create another character
        another_character = Character(
            name="Another Character",
            description="Another character for testing"
        )
        repo.create(another_character)
        
        # Act
        all_results = repo.list()
        
        # Assert
        assert len(all_results) == 2
        assert any(char.name == sample_character.name for char in all_results)
        assert any(char.name == another_character.name for char in all_results)
        
    def test_update(self, db_session, sample_character):
        """Test updating a Character entity."""
        # Arrange
        repo = SQLAlchemyCharacterRepository(db_session)
        created = repo.create(sample_character)
        
        # Modify the entity
        created.name = "Updated Character Name"
        created.description = "Updated character description"
        
        # Act
        updated = repo.update(created)
        
        # Assert
        assert updated.name == "Updated Character Name"
        assert updated.description == "Updated character description"
        
        # Verify by getting from repository
        fetched = repo.get_by_id(created.id)
        assert fetched.name == "Updated Character Name"
        assert fetched.description == "Updated character description"
        
    def test_delete(self, db_session, sample_character):
        """Test deleting a Character entity."""
        # Arrange
        repo = SQLAlchemyCharacterRepository(db_session)
        created = repo.create(sample_character)
        
        # Act
        result = repo.delete(created.id)
        
        # Assert
        assert result is True
        assert repo.get_by_id(created.id) is None
        
    def test_delete_not_found(self, db_session):
        """Test deleting a non-existent Character entity."""
        # Arrange
        repo = SQLAlchemyCharacterRepository(db_session)
        
        # Act
        result = repo.delete(uuid.uuid4())
        
        # Assert
        assert result is False
        
    def test_get_by_name(self, db_session, sample_character):
        """Test retrieving Character entities by name."""
        # Arrange
        repo = SQLAlchemyCharacterRepository(db_session)
        repo.create(sample_character)  # "Test Character"
        
        # Create another character
        another_character = Character(
            name="Another Test",
            description="Another character for testing"
        )
        repo.create(another_character)
        
        # Act
        results_test = repo.get_by_name("Test")
        results_another = repo.get_by_name("Another")
        results_nonexistent = repo.get_by_name("Nonexistent")
        
        # Assert
        assert len(results_test) == 2  # Should match both characters
        assert len(results_another) == 1
        assert len(results_nonexistent) == 0
        
    def test_get_by_voice_id(self, db_session, sample_character):
        """Test retrieving Character entities by voice ID."""
        # Arrange
        repo = SQLAlchemyCharacterRepository(db_session)
        
        # Create a character with a voice ID
        voice_id = uuid.uuid4()
        sample_character.voice_id = voice_id
        repo.create(sample_character)
        
        # Create another character with a different voice ID
        another_voice_id = uuid.uuid4()
        another_character = Character(
            name="Another Character",
            description="Another character with a different voice"
        )
        another_character.voice_id = another_voice_id
        repo.create(another_character)
        
        # Act
        results_first_voice = repo.get_by_voice_id(voice_id)
        results_second_voice = repo.get_by_voice_id(another_voice_id)
        results_nonexistent = repo.get_by_voice_id(uuid.uuid4())
        
        # Assert
        assert len(results_first_voice) == 1
        assert len(results_second_voice) == 1
        assert len(results_nonexistent) == 0
        assert results_first_voice[0].name == sample_character.name
        assert results_second_voice[0].name == another_character.name 