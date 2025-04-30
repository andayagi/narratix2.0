"""Base SQLAlchemy repository implementation."""
from typing import Generic, TypeVar, List, Optional, Type, Any, Dict
from uuid import UUID

from sqlalchemy.orm import Session

from narratix.core.domain.repositories.base_repository import BaseRepository

# Generic types for domain entities and SQLAlchemy models
T = TypeVar('T')  # Domain entity
M = TypeVar('M')  # SQLAlchemy model


class BaseSQLAlchemyRepository(Generic[T, M], BaseRepository[T]):
    """
    Base implementation of repository using SQLAlchemy ORM.
    
    This class provides the common CRUD operations for all repositories
    using SQLAlchemy as the persistence mechanism.
    """
    
    def __init__(self, session: Session, model_class: Type[M], entity_class: Type[T]):
        """
        Initialize the repository with a SQLAlchemy session and model/entity classes.
        
        Args:
            session: SQLAlchemy session for database operations
            model_class: The SQLAlchemy model class
            entity_class: The domain entity class
        """
        self._session = session
        self._model_class = model_class
        self._entity_class = entity_class
    
    def create(self, entity: T) -> T:
        """
        Persist a new entity.
        
        Args:
            entity: Domain entity to persist
            
        Returns:
            The persisted entity with any generated fields populated
        """
        # Convert domain entity to database model
        db_model = self._to_model(entity)
        
        # Add and commit
        self._session.add(db_model)
        self._session.commit()
        
        # Convert back to domain entity and return
        return self._to_entity(db_model)
    
    def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """
        Retrieve an entity by its unique identifier.
        
        Args:
            entity_id: UUID of the entity to retrieve
            
        Returns:
            The domain entity if found, None otherwise
        """
        db_model = self._session.query(self._model_class).filter_by(id=entity_id).first()
        
        if db_model is None:
            return None
            
        return self._to_entity(db_model)
    
    def list(self, **filters) -> List[T]:
        """
        Retrieve a list of entities, optionally filtered.
        
        Args:
            **filters: Filter criteria for the query
            
        Returns:
            List of domain entities matching the filter criteria
        """
        query = self._session.query(self._model_class)
        
        # Apply filters if provided
        if filters:
            query = query.filter_by(**filters)
            
        db_models = query.all()
        return [self._to_entity(model) for model in db_models]
    
    def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: Domain entity with updated fields
            
        Returns:
            The updated domain entity
            
        Raises:
            ValueError: If the entity does not exist
        """
        # Get entity ID (assumes all entities have an id attribute)
        entity_id = getattr(entity, 'id', None)
        if entity_id is None:
            raise ValueError("Entity must have an ID to be updated")
            
        # Check if entity exists
        db_model = self._session.query(self._model_class).filter_by(id=entity_id).first()
        if db_model is None:
            raise ValueError(f"Entity with ID {entity_id} not found")
            
        # Update model with entity attributes
        updated_model = self._update_model(db_model, entity)
        
        # Commit changes
        self._session.commit()
        
        # Convert back to domain entity and return
        return self._to_entity(updated_model)
    
    def delete(self, entity_id: UUID) -> bool:
        """
        Delete an entity by its unique identifier.
        
        Args:
            entity_id: UUID of the entity to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        db_model = self._session.query(self._model_class).filter_by(id=entity_id).first()
        
        if db_model is None:
            return False
            
        self._session.delete(db_model)
        self._session.commit()
        return True
    
    # Helper methods to be implemented by subclasses
    
    def _to_model(self, entity: T) -> M:
        """
        Convert a domain entity to a database model.
        
        Args:
            entity: Domain entity
            
        Returns:
            Database model
        """
        raise NotImplementedError("Subclasses must implement _to_model")
    
    def _to_entity(self, model: M) -> T:
        """
        Convert a database model to a domain entity.
        
        Args:
            model: Database model
            
        Returns:
            Domain entity
        """
        raise NotImplementedError("Subclasses must implement _to_entity")
    
    def _update_model(self, model: M, entity: T) -> M:
        """
        Update a database model with values from a domain entity.
        
        Args:
            model: Database model to update
            entity: Domain entity with updated values
            
        Returns:
            Updated database model
        """
        raise NotImplementedError("Subclasses must implement _update_model") 