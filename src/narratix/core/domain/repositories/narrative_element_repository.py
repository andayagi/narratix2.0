"""NarrativeElement repository interface."""
from typing import List, Optional
from uuid import UUID

from .base_repository import BaseRepository
from ..entities.narrative_element import NarrativeElement


class NarrativeElementRepository(BaseRepository[NarrativeElement]):
    """
    Repository interface for NarrativeElement entities.
    
    Defines the contract for NarrativeElement persistence operations.
    """
    
    def get_by_text_content_id(self, text_content_id: UUID) -> List[NarrativeElement]:
        """
        Retrieve NarrativeElements associated with a specific TextContent.
        
        Args:
            text_content_id: UUID of the TextContent
            
        Returns:
            List of NarrativeElement entities associated with the TextContent
        """
        pass
    
    def get_by_character_id(self, character_id: UUID) -> List[NarrativeElement]:
        """
        Retrieve NarrativeElements associated with a specific Character.
        
        Args:
            character_id: UUID of the Character
            
        Returns:
            List of NarrativeElement entities associated with the Character
        """
        pass
    
    def get_by_element_type(self, element_type: str) -> List[NarrativeElement]:
        """
        Retrieve NarrativeElements of a specific type.
        
        Args:
            element_type: Type of narrative element (e.g., 'dialogue', 'narration')
            
        Returns:
            List of NarrativeElement entities of the specified type
        """
        pass 