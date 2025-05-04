from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, TypeVar, Generic
import asyncio

T = TypeVar('T')

class RepositoryInterface(Generic[T], ABC):
    """Generic interface for data storage repositories."""
    
    @abstractmethod
    async def save(self, entity: T) -> str:
        """Save an entity to storage.
        
        Args:
            entity: Entity to save
            
        Returns:
            ID of the saved entity
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Retrieve an entity by ID.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            Entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """Retrieve entities matching criteria.
        
        Args:
            criteria: Dictionary of field-value pairs to match
            
        Returns:
            List of matching entities
        """
        pass
    
    @abstractmethod
    async def update(self, entity_id: str, data: Dict[str, Any]) -> bool:
        """Update an entity.
        
        Args:
            entity_id: ID of the entity
            data: Dictionary of field-value pairs to update
            
        Returns:
            True if update was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass 