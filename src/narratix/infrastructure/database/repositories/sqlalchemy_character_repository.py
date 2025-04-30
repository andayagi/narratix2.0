"""SQLAlchemy implementation of the CharacterRepository."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from narratix.core.domain.entities.character import Character as DomainCharacter
from narratix.core.domain.repositories.character_repository import CharacterRepository
from narratix.infrastructure.database.models import Character as DBCharacter
from .base_sqlalchemy_repository import BaseSQLAlchemyRepository


class SQLAlchemyCharacterRepository(
    BaseSQLAlchemyRepository[DomainCharacter, DBCharacter],
    CharacterRepository
):
    """SQLAlchemy implementation of the CharacterRepository."""
    
    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        super().__init__(session, DBCharacter, DomainCharacter)
    
    def get_by_name(self, name: str) -> List[DomainCharacter]:
        """
        Retrieve Characters by name.
        
        Args:
            name: Character name to search for
            
        Returns:
            List of Character entities matching the name
        """
        # Use ILIKE for case-insensitive name search
        query = self._session.query(self._model_class).filter(
            self._model_class.name.ilike(f"%{name}%")
        )
        db_models = query.all()
        return [self._to_entity(model) for model in db_models]
    
    def get_by_voice_id(self, voice_id: UUID) -> List[DomainCharacter]:
        """
        Retrieve Characters associated with a specific voice.
        
        Args:
            voice_id: UUID of the voice
            
        Returns:
            List of Character entities using the specified voice
        """
        db_models = self._session.query(self._model_class).filter_by(
            voice_id=voice_id
        ).all()
        return [self._to_entity(model) for model in db_models]
    
    def _to_model(self, entity: DomainCharacter) -> DBCharacter:
        """
        Convert a domain Character entity to a database model.
        
        Args:
            entity: Domain Character entity
            
        Returns:
            Database Character model
        """
        # If the entity already has an ID, create model with that ID
        if hasattr(entity, 'id') and entity.id is not None:
            db_model = DBCharacter(
                id=entity.id,
                name=entity.name,
                description=entity.description,
                voice_id=entity.voice_id if hasattr(entity, 'voice_id') else None
            )
        else:
            # Otherwise, let the database generate an ID
            db_model = DBCharacter(
                name=entity.name,
                description=entity.description,
                voice_id=entity.voice_id if hasattr(entity, 'voice_id') else None
            )
        
        return db_model
    
    def _to_entity(self, model: DBCharacter) -> DomainCharacter:
        """
        Convert a database Character model to a domain entity.
        
        Args:
            model: Database Character model
            
        Returns:
            Domain Character entity
        """
        entity = DomainCharacter(
            name=model.name,
            description=model.description
        )
        
        # Set the ID and voice_id attributes directly
        entity.id = model.id
        entity.voice_id = model.voice_id
        
        return entity
    
    def _update_model(self, model: DBCharacter, entity: DomainCharacter) -> DBCharacter:
        """
        Update a database Character model with values from a domain entity.
        
        Args:
            model: Database Character model to update
            entity: Domain Character entity with updated values
            
        Returns:
            Updated database Character model
        """
        model.name = entity.name
        model.description = entity.description
        
        # Only update voice_id if it exists on the entity
        if hasattr(entity, 'voice_id'):
            model.voice_id = entity.voice_id
        
        return model 