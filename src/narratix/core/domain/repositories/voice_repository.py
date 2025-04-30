"""Voice repository interface."""
from typing import List, Optional
from uuid import UUID

from .base_repository import BaseRepository
from ..entities.voice import Voice


class VoiceRepository(BaseRepository[Voice]):
    """
    Repository interface for Voice entities.
    
    Defines the contract for Voice persistence operations.
    """
    
    def get_by_provider(self, provider: str) -> List[Voice]:
        """
        Retrieve Voices from a specific provider.
        
        Args:
            provider: Name of the provider (e.g., 'aws', 'google')
            
        Returns:
            List of Voice entities from the specified provider
        """
        pass
    
    def get_by_gender(self, gender: str) -> List[Voice]:
        """
        Retrieve Voices of a specific gender.
        
        Args:
            gender: Gender of the voice (e.g., 'male', 'female')
            
        Returns:
            List of Voice entities matching the gender
        """
        pass
    
    def get_by_accent(self, accent: str) -> List[Voice]:
        """
        Retrieve Voices with a specific accent.
        
        Args:
            accent: Accent of the voice (e.g., 'british', 'american')
            
        Returns:
            List of Voice entities with the specified accent
        """
        pass 