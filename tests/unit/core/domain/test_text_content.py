import pytest
from narratix.core.domain.entities.text_content import TextContent

def test_text_content_initialization():
    """Test basic initialization of TextContent."""
    content = "This is a test."
    language = "en"
    metadata = {"source": "test"}
    
    text_content = TextContent(content=content, language=language, metadata=metadata)
    
    assert text_content.content == content
    assert text_content.language == language
    assert text_content.metadata == metadata

def test_text_content_default_language_and_metadata():
    """Test initialization with default language and metadata."""
    content = "Another test."
    
    text_content = TextContent(content=content)
    
    assert text_content.content == content
    assert text_content.language == "en"  # Default language
    assert text_content.metadata == {}      # Default metadata

def test_text_content_empty_content_raises_error():
    """Test that initializing with empty content raises ValueError."""
    with pytest.raises(ValueError, match="Content cannot be empty"):
        TextContent(content="") 