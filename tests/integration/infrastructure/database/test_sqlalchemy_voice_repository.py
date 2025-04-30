import pytest
from uuid import uuid4

from narratix.core.domain.entities.voice import Voice as DomainVoice
from narratix.infrastructure.database.repositories.sqlalchemy_voice_repository import SQLAlchemyVoiceRepository

# Tests rely on the db_session fixture from tests/conftest.py

def test_add_and_get_voice(db_session):
    """Test adding a Voice entity and retrieving it by ID."""
    repo = SQLAlchemyVoiceRepository(db_session)
    
    # Create a domain entity
    voice_id = "test-voice-id"
    voice_name = "Test Voice"
    provider = "test-provider"
    gender = "neutral"
    accent = "US English"
    voice_description = "A voice for integration test"
    
    domain_entity = DomainVoice(
        voice_id=voice_id,
        voice_name=voice_name,
        provider=provider,
        gender=gender,
        accent=accent,
        voice_description=voice_description
    )
    
    # Add to repository
    added_entity = repo.create(domain_entity)
    
    # Retrieve by ID
    retrieved_entity = repo.get_by_id(added_entity.id)
    
    assert retrieved_entity is not None
    assert retrieved_entity.id == added_entity.id
    assert retrieved_entity.voice_id == voice_id
    assert retrieved_entity.voice_name == voice_name
    assert retrieved_entity.provider == provider
    assert retrieved_entity.gender == gender
    assert retrieved_entity.accent == accent
    assert retrieved_entity.voice_description == voice_description

def test_get_non_existent_voice(db_session):
    """Test retrieving a non-existent Voice returns None."""
    repo = SQLAlchemyVoiceRepository(db_session)
    
    non_existent_id = uuid4()  # Generate a random UUID
    retrieved_entity = repo.get_by_id(non_existent_id)
    
    assert retrieved_entity is None

def test_list_voices(db_session):
    """Test listing Voice entities."""
    repo = SQLAlchemyVoiceRepository(db_session)
    
    # Add a couple of entities
    entity1 = DomainVoice(
        voice_id="voice-id-1",
        voice_name="Voice 1", 
        provider="provider-1"
    )
    entity2 = DomainVoice(
        voice_id="voice-id-2",
        voice_name="Voice 2", 
        provider="provider-2"
    )
    
    repo.create(entity1)
    repo.create(entity2)
    
    all_entities = repo.list()
    
    assert len(all_entities) >= 2
    voice_names = {e.voice_name for e in all_entities}
    assert "Voice 1" in voice_names
    assert "Voice 2" in voice_names

def test_get_by_provider(db_session):
    """Test retrieving Voices by provider."""
    repo = SQLAlchemyVoiceRepository(db_session)
    
    # Add test entities with different providers
    entity1 = DomainVoice(voice_id="a1", voice_name="Voice A", provider="amazon")
    entity2 = DomainVoice(voice_id="a2", voice_name="Voice B", provider="amazon")
    entity3 = DomainVoice(voice_id="g1", voice_name="Voice C", provider="google")
    
    repo.create(entity1)
    repo.create(entity2)
    repo.create(entity3)
    
    # Get voices by provider
    amazon_voices = repo.get_by_provider("amazon")
    
    assert len(amazon_voices) == 2
    amazon_voice_names = {e.voice_name for e in amazon_voices}
    assert "Voice A" in amazon_voice_names
    assert "Voice B" in amazon_voice_names
    assert "Voice C" not in amazon_voice_names

def test_get_by_gender(db_session):
    """Test retrieving Voices by gender."""
    repo = SQLAlchemyVoiceRepository(db_session)
    
    # Add test entities with different genders
    entity1 = DomainVoice(voice_id="m1", voice_name="Male Voice 1", provider="test", gender="male")
    entity2 = DomainVoice(voice_id="m2", voice_name="Male Voice 2", provider="test", gender="male")
    entity3 = DomainVoice(voice_id="f1", voice_name="Female Voice", provider="test", gender="female")
    
    repo.create(entity1)
    repo.create(entity2)
    repo.create(entity3)
    
    # Get voices by gender
    male_voices = repo.get_by_gender("male")
    female_voices = repo.get_by_gender("female")
    
    assert len(male_voices) == 2
    assert len(female_voices) == 1
    
    male_voice_names = {e.voice_name for e in male_voices}
    assert "Male Voice 1" in male_voice_names
    assert "Male Voice 2" in male_voice_names
    assert "Female Voice" not in male_voice_names
    
    female_voice_names = {e.voice_name for e in female_voices}
    assert "Female Voice" in female_voice_names

def test_get_by_language(db_session):
    """Test retrieving Voices by language (using accent as a proxy)."""
    repo = SQLAlchemyVoiceRepository(db_session)
    
    # Add test entities with different accents
    entity1 = DomainVoice(voice_id="t1", voice_name="English Voice 1", provider="test", accent="en-US")
    entity2 = DomainVoice(voice_id="t2", voice_name="English Voice 2", provider="test", accent="en-GB")
    entity3 = DomainVoice(voice_id="t3", voice_name="French Voice", provider="test", accent="fr-FR")
    
    repo.create(entity1)
    repo.create(entity2)
    repo.create(entity3)
    
    # Get voices by accent
    us_accent_voices = repo.get_by_accent("en-US")
    
    assert len(us_accent_voices) == 1
    assert us_accent_voices[0].voice_name == "English Voice 1"
    
    gb_accent_voices = repo.get_by_accent("en-GB")
    assert len(gb_accent_voices) == 1
    assert gb_accent_voices[0].voice_name == "English Voice 2"

def test_update_voice(db_session):
    """Test updating a Voice entity."""
    repo = SQLAlchemyVoiceRepository(db_session)
    
    # Create and add a voice
    voice = DomainVoice(
        voice_id="original-id",
        voice_name="Original Voice", 
        provider="original-provider"
    )
    added_voice = repo.create(voice)
    
    # Update the voice
    added_voice.voice_name = "Updated Voice"
    added_voice.voice_description = "Updated description"
    added_voice.gender = "female"
    
    updated_voice = repo.update(added_voice)
    
    # Retrieve to verify update
    retrieved_voice = repo.get_by_id(added_voice.id)
    
    assert retrieved_voice.voice_name == "Updated Voice"
    assert retrieved_voice.voice_description == "Updated description"
    assert retrieved_voice.gender == "female"
    assert retrieved_voice.provider == "original-provider"  # Unchanged

def test_delete_voice(db_session):
    """Test deleting a Voice entity."""
    repo = SQLAlchemyVoiceRepository(db_session)
    
    # Create and add a voice
    voice = DomainVoice(
        voice_id="delete-me",
        voice_name="To Delete", 
        provider="test"
    )
    added_voice = repo.create(voice)
    
    # Verify it exists
    assert repo.get_by_id(added_voice.id) is not None
    
    # Delete it
    success = repo.delete(added_voice.id)
    
    # Verify deletion
    assert success is True
    assert repo.get_by_id(added_voice.id) is None 