"""Repository interfaces for Narratix.

This module defines the base repository interface and specific repositories.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Generic, TypeVar, Type

T = TypeVar('T')


class RepositoryInterface(Generic[T], ABC):
    """Base interface for all repositories."""
    
    @abstractmethod
    def add(self, entity: T) -> T:
        """Add an entity to the repository.
        
        Args:
            entity: The entity to add
            
        Returns:
            The added entity with any generated IDs
        """
        pass
    
    @abstractmethod
    def get(self, entity_id: str) -> Optional[T]:
        """Get an entity by ID.
        
        Args:
            entity_id: ID of entity to retrieve
            
        Returns:
            Entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update(self, entity: T) -> T:
        """Update an entity in the repository.
        
        Args:
            entity: The entity to update
            
        Returns:
            The updated entity
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete an entity from the repository.
        
        Args:
            entity_id: ID of entity to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[T]:
        """List entities matching filters.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List of entities matching filters
        """
        pass


# Import domain entities to define specific repositories
from narratix.domain.entities import (
    TextContent,
    Character,
    Voice,
    NarrativeElement,
    AudioSegment
)


class TextContentRepository(RepositoryInterface[TextContent], ABC):
    """Repository for TextContent entities."""
    
    @abstractmethod
    def get_children(self, parent_id: str) -> List[TextContent]:
        """Get children of a TextContent entity.
        
        Args:
            parent_id: ID of the parent entity
            
        Returns:
            List of child TextContent entities
        """
        pass
    
    @abstractmethod
    def get_full_hierarchy(self, root_id: str) -> TextContent:
        """Get a TextContent entity with all its children recursively.
        
        Args:
            root_id: ID of the root entity
            
        Returns:
            TextContent with all children populated
        """
        pass


class CharacterRepository(RepositoryInterface[Character], ABC):
    """Repository for Character entities."""
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Character]:
        """Get a character by name.
        
        Args:
            name: Name of character to retrieve
            
        Returns:
            Character if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_narrators(self) -> List[Character]:
        """Get all narrator characters.
        
        Returns:
            List of characters with is_narrator=True
        """
        pass


class VoiceRepository(RepositoryInterface[Voice], ABC):
    """Repository for Voice entities."""
    
    @abstractmethod
    def get_by_character_id(self, character_id: str) -> Optional[Voice]:
        """Get a voice for a character.
        
        Args:
            character_id: ID of character to get voice for
            
        Returns:
            Voice if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_by_provider_id(self, provider_id: str) -> Optional[Voice]:
        """Get a voice by provider ID.
        
        Args:
            provider_id: Provider-specific ID
            
        Returns:
            Voice if found, None otherwise
        """
        pass


class NarrativeElementRepository(RepositoryInterface[NarrativeElement], ABC):
    """Repository for NarrativeElement entities."""
    
    @abstractmethod
    def get_by_text_content_id(self, text_content_id: str) -> List[NarrativeElement]:
        """Get narrative elements for a text content.
        
        Args:
            text_content_id: ID of text content
            
        Returns:
            List of narrative elements associated with the text content
        """
        pass
    
    @abstractmethod
    def get_by_character_id(self, character_id: str) -> List[NarrativeElement]:
        """Get narrative elements for a character.
        
        Args:
            character_id: ID of character
            
        Returns:
            List of narrative elements associated with the character
        """
        pass


class AudioSegmentRepository(RepositoryInterface[AudioSegment], ABC):
    """Repository for AudioSegment entities."""
    
    @abstractmethod
    def get_by_narrative_element_id(self, narrative_element_id: str) -> Optional[AudioSegment]:
        """Get audio segment for a narrative element.
        
        Args:
            narrative_element_id: ID of narrative element
            
        Returns:
            AudioSegment if found, None otherwise
        """
        pass 