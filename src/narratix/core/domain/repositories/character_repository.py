"""Character repository interface."""
from typing import List, Optional
from uuid import UUID

from .base_repository import BaseRepository
from ..entities.character import Character


class CharacterRepository(BaseRepository[Character]):
    """
    Repository interface for Character entities.
    
    Defines the contract for Character persistence operations.
    """
    
    def get_by_name(self, name: str) -> List[Character]:
        """
        Retrieve Characters by name.
        
        Args:
            name: Character name to search for
            
        Returns:
            List of Character entities matching the name
        """
        pass
    
    def get_by_voice_id(self, voice_id: UUID) -> List[Character]:
        """
        Retrieve Characters associated with a specific voice.
        
        Args:
            voice_id: UUID of the voice
            
        Returns:
            List of Character entities using the specified voice
        """
        pass 