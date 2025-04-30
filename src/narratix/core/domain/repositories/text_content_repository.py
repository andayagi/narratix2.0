"""TextContent repository interface."""
from typing import List, Optional
from uuid import UUID

from .base_repository import BaseRepository
from ..entities.text_content import TextContent


class TextContentRepository(BaseRepository[TextContent]):
    """
    Repository interface for TextContent entities.
    
    Defines the contract for TextContent persistence operations.
    """
    
    def search_by_content(self, search_term: str) -> List[TextContent]:
        """
        Search for TextContent entities that contain the given term.
        
        Args:
            search_term: Term to search for in content field
            
        Returns:
            List of TextContent entities containing the search term
        """
        pass
    
    def get_by_language(self, language_code: str) -> List[TextContent]:
        """
        Retrieve TextContent entities by language.
        
        Args:
            language_code: Language code (e.g., 'en', 'es')
            
        Returns:
            List of TextContent entities in the specified language
        """
        pass 