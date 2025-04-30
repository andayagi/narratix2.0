"""SQLAlchemy implementation of the VoiceRepository."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from narratix.core.domain.entities.voice import Voice as DomainVoice
from narratix.core.domain.repositories.voice_repository import VoiceRepository
from narratix.infrastructure.database.models import Voice as DBVoice
from .base_sqlalchemy_repository import BaseSQLAlchemyRepository


class SQLAlchemyVoiceRepository(
    BaseSQLAlchemyRepository[DomainVoice, DBVoice],
    VoiceRepository
):
    """SQLAlchemy implementation of the VoiceRepository."""
    
    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        super().__init__(session, DBVoice, DomainVoice)
    
    def get_by_provider(self, provider: str) -> List[DomainVoice]:
        """
        Retrieve Voices from a specific provider.
        
        Args:
            provider: Name of the provider (e.g., 'aws', 'google')
            
        Returns:
            List of Voice entities from the specified provider
        """
        db_models = self._session.query(self._model_class).filter_by(
            provider=provider
        ).all()
        return [self._to_entity(model) for model in db_models]
    
    def get_by_gender(self, gender: str) -> List[DomainVoice]:
        """
        Retrieve Voices of a specific gender.
        
        Args:
            gender: Gender of the voice (e.g., 'male', 'female')
            
        Returns:
            List of Voice entities matching the gender
        """
        db_models = self._session.query(self._model_class).filter_by(
            gender=gender
        ).all()
        return [self._to_entity(model) for model in db_models]
    
    def get_by_accent(self, accent: str) -> List[DomainVoice]:
        """
        Retrieve Voices with a specific accent.
        
        Args:
            accent: Accent of the voice (e.g., 'british', 'american')
            
        Returns:
            List of Voice entities with the specified accent
        """
        db_models = self._session.query(self._model_class).filter_by(
            accent=accent
        ).all()
        return [self._to_entity(model) for model in db_models]
    
    def _to_model(self, entity: DomainVoice) -> DBVoice:
        """
        Convert a domain Voice entity to a database model.
        
        Args:
            entity: Domain Voice entity
            
        Returns:
            Database Voice model
        """
        # If the entity already has an ID, create model with that ID
        if hasattr(entity, 'id') and entity.id is not None:
            db_model = DBVoice(
                id=entity.id,
                voice_id=entity.voice_id,
                voice_name=entity.voice_name,
                provider=entity.provider,
                gender=entity.gender,
                accent=entity.accent,
                voice_description=entity.voice_description,
                pitch=entity.pitch
            )
        else:
            # Otherwise, let the database generate an ID
            db_model = DBVoice(
                voice_id=entity.voice_id,
                voice_name=entity.voice_name,
                provider=entity.provider,
                gender=entity.gender,
                accent=entity.accent,
                voice_description=entity.voice_description,
                pitch=entity.pitch
            )
        
        return db_model
    
    def _to_entity(self, model: DBVoice) -> DomainVoice:
        """
        Convert a database Voice model to a domain entity.
        
        Args:
            model: Database Voice model
            
        Returns:
            Domain Voice entity
        """
        entity = DomainVoice(
            voice_id=model.voice_id,
            voice_name=model.voice_name,
            provider=model.provider,
            gender=model.gender,
            accent=model.accent,
            voice_description=model.voice_description,
            pitch=model.pitch
        )
        
        # Set the ID attribute directly
        entity.id = model.id
        
        return entity
    
    def _update_model(self, model: DBVoice, entity: DomainVoice) -> DBVoice:
        """
        Update a database Voice model with values from a domain entity.
        
        Args:
            model: Database Voice model to update
            entity: Domain Voice entity with updated values
            
        Returns:
            Updated database Voice model
        """
        model.voice_id = entity.voice_id
        model.voice_name = entity.voice_name
        model.provider = entity.provider
        model.gender = entity.gender
        model.accent = entity.accent
        model.voice_description = entity.voice_description
        model.pitch = entity.pitch
        
        return model 