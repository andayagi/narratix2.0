"""TextContent entity representing the input text to be processed."""
from typing import Dict, Optional, List


class TextContent:
    """
    Represents the input text to be processed for narrative conversion.
    
    This entity serves as the source material from which narrative elements
    are derived for audio conversion.
    """
    
    def __init__(
        self, 
        content: str, 
        language: str = "en", 
        metadata: Optional[Dict] = None
    ):
        """
        Initialize a new TextContent instance.
        
        Args:
            content: The raw text content to be processed.
            language: Detected or specified language code (e.g., 'en', 'es').
                      Defaults to English ('en').
            metadata: Optional dictionary containing metadata about the text
                     (e.g., source, author, creation date).
        """
        self.content = content
        self.language = language
        self.metadata = metadata or {}
        
        # Perform basic validation on initialization
        self.validate()
        
    def segment(self) -> List[str]:
        """
        Break text into processable chunks (sentences, paragraphs).
        
        Returns:
            A list of text segments.
        """
        # This is a placeholder implementation
        # In a real implementation, this would use NLP techniques for proper segmentation
        return [s.strip() for s in self.content.split(".") if s.strip()]
    
    def validate(self) -> bool:
        """
        Check for invalid characters or excessive length.
        
        Returns:
            True if the content is valid, raises ValueError otherwise.
        """
        if not self.content:
            raise ValueError("Content cannot be empty")
        
        # Basic length validation - can be adjusted based on needs
        if len(self.content) > 100000:  # Example limit of 100K chars
            raise ValueError("Content exceeds maximum allowed length")
            
        return True
    
    def __str__(self) -> str:
        """Return a string representation of the TextContent."""
        return f"TextContent(language={self.language}, length={len(self.content)})" 