"""
Protocol defining the interface for voice management services.
"""
from typing import Protocol, List, Dict, Any, Optional
from src.narratix.core.domain.entities.voice import Voice
from src.narratix.core.domain.entities.character import Character


class VoiceManagementService(Protocol):
    """
    Interface for voice management operations.
    
    This service handles the management of voice profiles, including
    creation, retrieval, and association with characters.
    """
    
    def get_available_voices(self) -> List[Voice]:
        """
        Get a list of all available voices.
        
        Returns:
            A list of available Voice objects.
        """
        ...
    
    def get_voice_by_id(self, voice_id: str) -> Optional[Voice]:
        """
        Get a voice by its identifier.
        
        Args:
            voice_id: The unique identifier of the voice.
            
        Returns:
            The Voice object if found, None otherwise.
        """
        ...
    
    def filter_voices(self, criteria: Dict[str, Any]) -> List[Voice]:
        """
        Filter voices based on the given criteria.
        
        Args:
            criteria: A dictionary of filtering criteria (e.g., gender,
                     age_range, accent, etc.).
                     
        Returns:
            A list of Voice objects matching the criteria.
        """
        ...
    
    def assign_voice_to_character(self, character: Character, voice: Voice) -> bool:
        """
        Assign a voice to a character.
        
        Args:
            character: The character to assign the voice to.
            voice: The voice to assign.
            
        Returns:
            True if the assignment was successful, False otherwise.
        """
        ...
    
    def create_custom_voice(self, voice_data: Dict[str, Any]) -> Voice:
        """
        Create a new custom voice profile.
        
        Args:
            voice_data: A dictionary containing voice parameters.
            
        Returns:
            The newly created Voice object.
        """
        ...
    
    def update_voice(self, voice_id: str, voice_data: Dict[str, Any]) -> Optional[Voice]:
        """
        Update an existing voice profile.
        
        Args:
            voice_id: The unique identifier of the voice to update.
            voice_data: A dictionary containing the updated voice parameters.
            
        Returns:
            The updated Voice object if found and updated, None otherwise.
        """
        ... 