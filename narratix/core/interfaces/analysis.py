from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio

class TextAnalysisInterface(ABC):
    """Interface for text analysis capabilities."""
    
    @abstractmethod
    async def analyze_text(self, text: str, force_reanalysis: bool = False) -> Dict[str, Any]:
        """Analyze text to identify characters and segment by voice.
        
        Args:
            text: The narrative text to analyze
            force_reanalysis: Force reanalysis even if we have cached results
            
        Returns:
            Dictionary containing analysis results with:
                - roles: List of character information
                - narrative_elements: List of text segments
                - meta: Analysis metadata
        """
        pass
    
    @abstractmethod
    async def get_existing_analysis(self, text_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis if available.
        
        Args:
            text_hash: Hash of the text content
            
        Returns:
            Dictionary containing analysis results or None if not found
        """
        pass
    
    @abstractmethod
    async def save_analysis(self, text_hash: str, analysis_data: Dict[str, Any]) -> str:
        """Save analysis results for future use.
        
        Args:
            text_hash: Hash of the text content
            analysis_data: Analysis results to save
            
        Returns:
            ID of the saved analysis
        """
        pass 