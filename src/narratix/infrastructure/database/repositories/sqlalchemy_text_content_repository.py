"""SQLAlchemy implementation of the TextContentRepository."""
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from narratix.core.domain.entities.text_content import TextContent as DomainTextContent
from narratix.core.domain.repositories.text_content_repository import TextContentRepository
from narratix.infrastructure.database.models import TextContent as DBTextContent
from .base_sqlalchemy_repository import BaseSQLAlchemyRepository


class SQLAlchemyTextContentRepository(
    BaseSQLAlchemyRepository[DomainTextContent, DBTextContent],
    TextContentRepository
):
    """SQLAlchemy implementation of the TextContentRepository."""
    
    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        super().__init__(session, DBTextContent, DomainTextContent)
    
    def search_by_content(self, search_term: str) -> List[DomainTextContent]:
        """
        Search for TextContent entities that contain the given term.
        
        Args:
            search_term: Term to search for in content field
            
        Returns:
            List of TextContent entities containing the search term
        """
        # Using LIKE for simple text search
        query = self._session.query(self._model_class).filter(
            self._model_class.content.ilike(f"%{search_term}%")
        )
        db_models = query.all()
        return [self._to_entity(model) for model in db_models]
    
    def get_by_language(self, language_code: str) -> List[DomainTextContent]:
        """
        Retrieve TextContent entities by language.
        
        Args:
            language_code: Language code (e.g., 'en', 'es')
            
        Returns:
            List of TextContent entities in the specified language
        """
        db_models = self._session.query(self._model_class).filter_by(
            language=language_code
        ).all()
        return [self._to_entity(model) for model in db_models]
    
    def _to_model(self, entity: DomainTextContent) -> DBTextContent:
        """
        Convert a domain TextContent entity to a database model.
        
        Args:
            entity: Domain TextContent entity
            
        Returns:
            Database TextContent model
        """
        # If the entity already has an ID, create model with that ID
        if hasattr(entity, 'id') and entity.id is not None:
            db_model = DBTextContent(
                id=entity.id,
                content=entity.content,
                language=entity.language,
                content_metadata=entity.metadata
            )
        else:
            # Otherwise, let the database generate an ID
            db_model = DBTextContent(
                content=entity.content,
                language=entity.language,
                content_metadata=entity.metadata
            )
        
        return db_model
    
    def _to_entity(self, model: DBTextContent) -> DomainTextContent:
        """
        Convert a database TextContent model to a domain entity.
        
        Args:
            model: Database TextContent model
            
        Returns:
            Domain TextContent entity
        """
        # Ensure metadata is a standard dict using the correct source attribute
        metadata_dict = dict(model.content_metadata or {})
        
        entity = DomainTextContent(
            content=model.content,
            language=model.language,
            metadata=metadata_dict
        )
        
        # Set the ID attribute directly
        entity.id = model.id
        
        return entity
    
    def _update_model(self, model: DBTextContent, entity: DomainTextContent) -> DBTextContent:
        """
        Update a database TextContent model with values from a domain entity.
        
        Args:
            model: Database TextContent model to update
            entity: Domain TextContent entity with updated values
            
        Returns:
            Updated database TextContent model
        """
        model.content = entity.content
        model.language = entity.language
        model.content_metadata = entity.metadata
        
        return model 