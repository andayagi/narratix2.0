"""SQLAlchemy implementation of the NarrativeElementRepository."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from narratix.core.domain.entities.narrative_element import NarrativeElement as DomainNarrativeElement
from narratix.core.domain.repositories.narrative_element_repository import NarrativeElementRepository
from narratix.infrastructure.database.models import NarrativeElement as DBNarrativeElement
from .base_sqlalchemy_repository import BaseSQLAlchemyRepository


class SQLAlchemyNarrativeElementRepository(
    BaseSQLAlchemyRepository[DomainNarrativeElement, DBNarrativeElement],
    NarrativeElementRepository
):
    """SQLAlchemy implementation of the NarrativeElementRepository."""
    
    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        super().__init__(session, DBNarrativeElement, DomainNarrativeElement)
    
    def get_by_text_content_id(self, text_content_id: UUID) -> List[DomainNarrativeElement]:
        """
        Retrieve NarrativeElements associated with a specific TextContent.
        
        Args:
            text_content_id: UUID of the TextContent
            
        Returns:
            List of NarrativeElement entities associated with the TextContent
        """
        db_models = self._session.query(self._model_class).filter_by(
            text_content_id=text_content_id
        ).all()
        return [self._to_entity(model) for model in db_models]
    
    def get_by_character_id(self, character_id: UUID) -> List[DomainNarrativeElement]:
        """
        Retrieve NarrativeElements associated with a specific Character.
        
        Args:
            character_id: UUID of the Character
            
        Returns:
            List of NarrativeElement entities associated with the Character
        """
        db_models = self._session.query(self._model_class).filter_by(
            character_id=character_id
        ).all()
        return [self._to_entity(model) for model in db_models]
    
    def get_by_element_type(self, element_type: str) -> List[DomainNarrativeElement]:
        """
        Retrieve NarrativeElements of a specific type.
        
        Args:
            element_type: Type of narrative element (e.g., 'dialogue', 'narration')
            
        Returns:
            List of NarrativeElement entities of the specified type
        """
        db_models = self._session.query(self._model_class).filter_by(
            element_type=element_type
        ).all()
        return [self._to_entity(model) for model in db_models]
    
    def _to_model(self, entity: DomainNarrativeElement) -> DBNarrativeElement:
        """
        Convert a domain NarrativeElement entity to a database model.
        
        Args:
            entity: Domain NarrativeElement entity
            
        Returns:
            Database NarrativeElement model
        """
        # If the entity already has an ID, create model with that ID
        if hasattr(entity, 'id') and entity.id is not None:
            db_model = DBNarrativeElement(
                id=entity.id,
                text_segment=entity.text_segment,
                start_offset=entity.start_offset,
                end_offset=entity.end_offset,
                element_type=entity.element_type,
                acting_instructions=entity.acting_instructions,
                speed=entity.speed,
                trailing_silence=entity.trailing_silence,
                text_content_id=entity.text_content_id,
                character_id=entity.character_id if hasattr(entity, 'character_id') else None
            )
        else:
            # Otherwise, let the database generate an ID
            db_model = DBNarrativeElement(
                text_segment=entity.text_segment,
                start_offset=entity.start_offset,
                end_offset=entity.end_offset,
                element_type=entity.element_type,
                acting_instructions=entity.acting_instructions,
                speed=entity.speed,
                trailing_silence=entity.trailing_silence,
                text_content_id=entity.text_content_id,
                character_id=entity.character_id if hasattr(entity, 'character_id') else None
            )
        
        return db_model
    
    def _to_entity(self, model: DBNarrativeElement) -> DomainNarrativeElement:
        """
        Convert a database NarrativeElement model to a domain entity.
        
        Args:
            model: Database NarrativeElement model
            
        Returns:
            Domain NarrativeElement entity
        """
        # Create a temporary character for testing purposes
        from narratix.core.domain.entities.character import Character
        temp_character = Character(name="Temp Character")
        
        entity = DomainNarrativeElement(
            text_segment=model.text_segment,
            start_offset=model.start_offset,
            end_offset=model.end_offset,
            element_type=model.element_type,
            character=temp_character,
            acting_instructions=model.acting_instructions,
            speed=model.speed,
            trailing_silence=model.trailing_silence
        )
        
        # Set the ID, text_content_id and character_id attributes directly
        entity.id = model.id
        entity.text_content_id = model.text_content_id
        entity.character_id = model.character_id
        
        return entity
    
    def _update_model(self, model: DBNarrativeElement, entity: DomainNarrativeElement) -> DBNarrativeElement:
        """
        Update a database NarrativeElement model with values from a domain entity.
        
        Args:
            model: Database NarrativeElement model to update
            entity: Domain NarrativeElement entity with updated values
            
        Returns:
            Updated database NarrativeElement model
        """
        model.text_segment = entity.text_segment
        model.start_offset = entity.start_offset
        model.end_offset = entity.end_offset
        model.element_type = entity.element_type
        model.acting_instructions = entity.acting_instructions
        model.speed = entity.speed
        model.trailing_silence = entity.trailing_silence
        model.text_content_id = entity.text_content_id
        
        # Only update character_id if it exists on the entity
        if hasattr(entity, 'character_id'):
            model.character_id = entity.character_id
        
        return model 