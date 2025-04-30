import unittest
from unittest.mock import patch, MagicMock
import os
from src.narratix.infrastructure.external.anthropic import AnthropicClient
import anthropic  # Import anthropic at the top level

# Mock the MessageParam class if needed, or use actual if simple
# For simplicity, we can just check the dictionary passed to messages.create

class TestAnthropicClient(unittest.TestCase):
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_api_key"})
    @patch("anthropic.Anthropic")
    def test_generate_completion(self, mock_anthropic):
        # Set up the mock for Anthropic client
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Set up the mock response from the messages.create call
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "This is a test response"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response
        
        # Create the client and call generate_completion
        client = AnthropicClient()
        response = client.generate_completion(
            prompt="Test prompt",
            model="claude-test",
            max_tokens=100,
            temperature=0.5
        )
        
        # Assert the client was called with the correct parameters
        mock_client.messages.create.assert_called_once()
        call_args, call_kwargs = mock_client.messages.create.call_args
        self.assertEqual(call_kwargs["model"], "claude-test")
        self.assertEqual(call_kwargs["max_tokens"], 100)
        self.assertEqual(call_kwargs["temperature"], 0.5)
        # Check the structure of the messages parameter
        self.assertIsInstance(call_kwargs["messages"], list)
        self.assertEqual(len(call_kwargs["messages"]), 1)
        # The anthropic library expects a list of dicts or MessageParam objects.
        # Let's check the dictionary passed.
        message_param = call_kwargs["messages"][0]
        self.assertIsInstance(message_param, dict) # Check if it's a dict as expected by the mock
        self.assertEqual(message_param['role'], "user")
        self.assertEqual(message_param['content'], "Test prompt")
        
        # Assert the response is correct
        self.assertEqual(response, "This is a test response")
    
    @patch.dict(os.environ, {})  # Empty environment
    def test_missing_api_key(self):
        # Test that the client raises an error when the API key is not set
        with self.assertRaises(ValueError):
            AnthropicClient()
    
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_api_key"})
    @patch("anthropic.Anthropic")
    def test_api_error_handling(self, mock_anthropic):
        # Set up the mock for Anthropic client
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Make the API call raise an exception
        # Mock the APIError correctly, it requires a 'request' argument
        mock_request = MagicMock() # Mock the request object
        mock_client.messages.create.side_effect = anthropic.APIError("Test API error", request=mock_request, body=None)
        
        # Create the client and test error handling
        client = AnthropicClient()
        with self.assertRaises(Exception) as context:
            client.generate_completion("Test prompt")
        
        self.assertIn("Error communicating with Anthropic API", str(context.exception))

if __name__ == "__main__":
    unittest.main() 