"""Base repository interface for all repository implementations."""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Any
from uuid import UUID

T = TypeVar('T')  # Generic type for entities


class BaseRepository(Generic[T], ABC):
    """
    Base repository interface defining standard CRUD operations.
    
    All concrete repository implementations should inherit from this interface.
    """
    
    @abstractmethod
    def create(self, entity: T) -> T:
        """
        Persist a new entity.
        
        Args:
            entity: The entity to persist
            
        Returns:
            The persisted entity with any generated fields (e.g., ID) populated
        """
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """
        Retrieve an entity by its unique identifier.
        
        Args:
            entity_id: The unique identifier of the entity
            
        Returns:
            The entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def list(self, **filters) -> List[T]:
        """
        Retrieve a list of entities, optionally filtered.
        
        Args:
            **filters: Optional filter criteria
            
        Returns:
            A list of entities matching the filter criteria
        """
        pass
    
    @abstractmethod
    def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: The entity with updated fields
            
        Returns:
            The updated entity
            
        Raises:
            ValueError: If the entity does not exist
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: UUID) -> bool:
        """
        Delete an entity by its unique identifier.
        
        Args:
            entity_id: The unique identifier of the entity to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass 