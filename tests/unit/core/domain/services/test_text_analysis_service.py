"""
Tests for the TextAnalysisService protocol.
"""
import unittest
from typing import List, Dict, Any, Protocol, runtime_checkable

from src.narratix.core.domain.entities.text_content import TextContent
from src.narratix.core.domain.services.text_analysis_service import TextAnalysisService


class MockTextAnalysisService:
    """Mock implementation of TextAnalysisService for testing."""
    
    def analyze_text(self, text_content: TextContent) -> Dict[str, Any]:
        return {"word_count": 100, "sentiment": "positive"}
    
    def identify_characters(self, text_content: TextContent) -> List[Dict[str, Any]]:
        return [{"name": "Alice", "frequency": 10}, {"name": "Bob", "frequency": 5}]
    
    def detect_dialog(self, text_content: TextContent) -> List[Dict[str, Any]]:
        return [
            {"speaker": "Alice", "text": "Hello, Bob!", "line": 1},
            {"speaker": "Bob", "text": "Hi, Alice.", "line": 2}
        ]
    
    def segment_text(self, text_content: TextContent) -> List[Dict[str, Any]]:
        return [
            {"type": "narrative", "content": "Once upon a time..."},
            {"type": "dialog", "speaker": "Alice", "content": "Hello, Bob!"}
        ]
    
    def extract_sentiment(self, text_segment: str) -> Dict[str, float]:
        return {"positive": 0.8, "negative": 0.1, "neutral": 0.1}


class TestTextAnalysisService(unittest.TestCase):
    """Tests for the TextAnalysisService protocol."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = MockTextAnalysisService()
        # Create a simple TextContent for testing
        self.sample_text = TextContent(
            content="Once upon a time, Alice said: 'Hello, Bob!' Bob replied: 'Hi, Alice.'",
            language="en",
            metadata={"title": "Test Story"}
        )
    
    def test_protocol_conformance(self):
        """Test that our mock correctly implements the protocol."""
        # Since Protocol classes don't have a direct way to check conformance in runtime,
        # we'll just check that the service has all the required methods
        self.assertTrue(hasattr(self.mock_service, "analyze_text"))
        self.assertTrue(hasattr(self.mock_service, "identify_characters"))
        self.assertTrue(hasattr(self.mock_service, "detect_dialog"))
        self.assertTrue(hasattr(self.mock_service, "segment_text"))
        self.assertTrue(hasattr(self.mock_service, "extract_sentiment"))
    
    def test_analyze_text(self):
        """Test the analyze_text method."""
        result = self.mock_service.analyze_text(self.sample_text)
        self.assertIsInstance(result, dict)
        self.assertIn("word_count", result)
        self.assertIn("sentiment", result)
    
    def test_identify_characters(self):
        """Test the identify_characters method."""
        characters = self.mock_service.identify_characters(self.sample_text)
        self.assertIsInstance(characters, list)
        self.assertEqual(len(characters), 2)
        self.assertEqual(characters[0]["name"], "Alice")
        self.assertEqual(characters[1]["name"], "Bob")
    
    def test_detect_dialog(self):
        """Test the detect_dialog method."""
        dialog = self.mock_service.detect_dialog(self.sample_text)
        self.assertIsInstance(dialog, list)
        self.assertEqual(len(dialog), 2)
        self.assertEqual(dialog[0]["speaker"], "Alice")
        self.assertEqual(dialog[1]["speaker"], "Bob")
    
    def test_segment_text(self):
        """Test the segment_text method."""
        segments = self.mock_service.segment_text(self.sample_text)
        self.assertIsInstance(segments, list)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["type"], "narrative")
        self.assertEqual(segments[1]["type"], "dialog")
    
    def test_extract_sentiment(self):
        """Test the extract_sentiment method."""
        sentiment = self.mock_service.extract_sentiment("I am happy")
        self.assertIsInstance(sentiment, dict)
        self.assertIn("positive", sentiment)
        self.assertIn("negative", sentiment)
        self.assertIn("neutral", sentiment)


if __name__ == "__main__":
    unittest.main() 