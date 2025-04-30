"""Unit tests for the TextContent entity."""
import pytest
from src.narratix.core.domain.entities import TextContent


class TestTextContent:
    """Test cases for the TextContent class."""
    
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        content = "This is sample content."
        text = TextContent(content)
        
        assert text.content == content
        assert text.language == "en"
        assert text.metadata == {}
        
    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        content = "Este es contenido de muestra."
        language = "es"
        metadata = {"author": "Test Author", "source": "Test Source"}
        
        text = TextContent(content, language, metadata)
        
        assert text.content == content
        assert text.language == language
        assert text.metadata == metadata
        
    def test_validate_empty_content(self):
        """Test validation with empty content."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            TextContent("")
            
    def test_validate_excessive_length(self):
        """Test validation with content exceeding maximum length."""
        long_content = "a" * 100001  # Exceeds the 100K limit
        
        with pytest.raises(ValueError, match="Content exceeds maximum allowed length"):
            TextContent(long_content)
            
    def test_segment(self):
        """Test the segment method."""
        content = "First sentence. Second sentence. Third sentence."
        text = TextContent(content)
        
        segments = text.segment()
        
        assert len(segments) == 3
        assert segments[0] == "First sentence"
        assert segments[1] == "Second sentence"
        assert segments[2] == "Third sentence"
        
    def test_str_representation(self):
        """Test string representation."""
        content = "Sample content."
        text = TextContent(content)
        
        expected_str = f"TextContent(language=en, length={len(content)})"
        assert str(text) == expected_str 