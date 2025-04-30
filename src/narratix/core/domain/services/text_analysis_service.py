"""
Protocol defining the interface for text analysis services.
"""
from typing import Protocol, List, Dict, Any, Optional
from src.narratix.core.domain.entities.text_content import TextContent


class TextAnalysisService(Protocol):
    """
    Interface for text analysis operations.
    
    This service handles text processing, analysis, and extraction of
    relevant features from text content.
    """
    
    def analyze_text(self, text_content: TextContent) -> Dict[str, Any]:
        """
        Analyze the given text content and extract relevant features.
        
        Args:
            text_content: The text content to analyze.
            
        Returns:
            A dictionary containing analysis results with various
            extracted features and metadata.
        """
        ...
    
    def identify_characters(self, text_content: TextContent) -> List[Dict[str, Any]]:
        """
        Identify potential characters in the text content.
        
        Args:
            text_content: The text content to analyze.
            
        Returns:
            A list of dictionaries containing character information
            extracted from the text.
        """
        ...
    
    def detect_dialog(self, text_content: TextContent) -> List[Dict[str, Any]]:
        """
        Detect and extract dialog segments from the text content.
        
        Args:
            text_content: The text content to analyze.
            
        Returns:
            A list of dictionaries containing dialog segments with
            speaker attribution when possible.
        """
        ...
    
    def segment_text(self, text_content: TextContent) -> List[Dict[str, Any]]:
        """
        Segment the text into logical narrative elements.
        
        Args:
            text_content: The text content to segment.
            
        Returns:
            A list of dictionaries representing narrative segments,
            potentially including type, speaker, and content.
        """
        ...
    
    def extract_sentiment(self, text_segment: str) -> Dict[str, float]:
        """
        Extract sentiment metrics from a text segment.
        
        Args:
            text_segment: The text segment to analyze.
            
        Returns:
            A dictionary containing sentiment metrics (e.g., positive,
            negative, neutral scores).
        """
        ... 