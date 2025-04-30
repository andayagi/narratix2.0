import unittest
import json
from unittest.mock import Mock, patch, ANY

from narratix.core.domain.entities import Character
# Adjust the import path if AnthropicClient is located elsewhere
from narratix.infrastructure.external.anthropic import AnthropicClient
from narratix.services.character_identification import AnthropicCharacterIdentificationService


class TestAnthropicCharacterIdentificationService(unittest.TestCase):

    def setUp(self):
        """Set up a mock client and the service before each test."""
        # Create a mock object for AnthropicClient with the create_message method
        self.mock_anthropic_client = Mock(spec=AnthropicClient)
        # Ensure create_message exists on the mock
        self.mock_anthropic_client.create_message = Mock()
        # Instantiate the service with the mock client
        self.service = AnthropicCharacterIdentificationService(client=self.mock_anthropic_client)
        # Define standard call args for convenience
        self.expected_model = "claude-3-5-haiku-20241022"
        self.expected_max_tokens = 8192
        self.expected_temperature = 1.0

    def test_identify_characters_success_third_person(self):
        """Test successful character identification for third-person text."""
        mock_response_json = {
            "characters": [
                {
                    "name": "Narrator",
                    "is_narrator": True,
                    "speaking": False,
                    "persona_description": "Desc for Narrator",
                    "text": "Intro for Narrator"
                },
                {
                    "name": "Maya",
                    "is_narrator": False,
                    "speaking": True,
                    "persona_description": "Desc for Maya",
                    "text": "Intro for Maya"
                },
                {
                    "name": "Kell",
                    "is_narrator": False,
                    "speaking": True,
                    "persona_description": "Desc for Kell",
                    "text": "Intro for Kell"
                }
            ]
        }
        # Simulate the client returning the JSON string
        self.mock_anthropic_client.create_message.return_value = json.dumps(mock_response_json)
        input_text = "Maya and Kell talked."

        characters = self.service.identify_characters(input_text)

        # Assertions
        self.mock_anthropic_client.create_message.assert_called_once_with(
            model=self.expected_model,
            max_tokens=self.expected_max_tokens,
            temperature=self.expected_temperature,
            messages=ANY # Check messages structure more deeply if needed
        )
        self.assertEqual(len(characters), 3)

        self.assertEqual(characters[0].name, "Narrator")
        self.assertTrue(characters[0].is_narrator)
        self.assertFalse(characters[0].speaking)
        self.assertEqual(characters[0].persona_description, "Desc for Narrator")
        self.assertEqual(characters[0].text, "Intro for Narrator")

        self.assertEqual(characters[1].name, "Maya")
        self.assertFalse(characters[1].is_narrator)
        self.assertTrue(characters[1].speaking)
        self.assertEqual(characters[1].persona_description, "Desc for Maya")
        self.assertEqual(characters[1].text, "Intro for Maya")

        self.assertEqual(characters[2].name, "Kell")
        self.assertFalse(characters[2].is_narrator)
        self.assertTrue(characters[2].speaking)
        self.assertEqual(characters[2].persona_description, "Desc for Kell")
        self.assertEqual(characters[2].text, "Intro for Kell")

    def test_identify_characters_success_first_person(self):
        """Test successful character identification for first-person text."""
        mock_response_json = {
            "characters": [
                {
                    "name": "protagonist", # As per prompt examples
                    "is_narrator": True,
                    "speaking": True,
                    "persona_description": "Desc for Protagonist",
                    "text": "Intro for Protagonist"
                },
                {
                    "name": "Kell",
                    "is_narrator": False,
                    "speaking": True,
                    "persona_description": "Desc for Kell",
                    "text": "Intro for Kell"
                }
            ]
        }
        self.mock_anthropic_client.create_message.return_value = json.dumps(mock_response_json)
        input_text = "I spoke with Kell."

        characters = self.service.identify_characters(input_text)

        self.mock_anthropic_client.create_message.assert_called_once()
        self.assertEqual(len(characters), 2)

        self.assertEqual(characters[0].name, "protagonist")
        self.assertTrue(characters[0].is_narrator)
        self.assertTrue(characters[0].speaking)
        self.assertEqual(characters[0].persona_description, "Desc for Protagonist")
        self.assertEqual(characters[0].text, "Intro for Protagonist")

        self.assertEqual(characters[1].name, "Kell")
        self.assertFalse(characters[1].is_narrator)
        self.assertTrue(characters[1].speaking)
        self.assertEqual(characters[1].persona_description, "Desc for Kell")
        self.assertEqual(characters[1].text, "Intro for Kell")

    def test_identify_characters_missing_required_field(self):
        """Test response where one character is missing a required field (e.g., speaking)."""
        mock_response_json = {
            "characters": [
                {
                    "name": "ValidChar",
                    "is_narrator": False,
                    "speaking": True,
                    "persona_description": "Desc Valid",
                    "text": "Intro Valid"
                },
                {
                    "name": "MissingSpeaking",
                    "is_narrator": False,
                    # "speaking": False, # Missing required field
                    "persona_description": "Desc Invalid",
                    "text": "Intro Invalid"
                },
                {
                    "name": "MissingNarratorFlag",
                    # "is_narrator": False, # Missing required field
                    "speaking": True,
                    "persona_description": "Desc Invalid 2",
                    "text": "Intro Invalid 2"
                }
            ]
        }
        self.mock_anthropic_client.create_message.return_value = json.dumps(mock_response_json)
        input_text = "Some text."

        # Use patch to capture print output for assertion
        with patch('builtins.print') as mock_print:
            characters = self.service.identify_characters(input_text)

        self.mock_anthropic_client.create_message.assert_called_once()
        # Should only return the valid character
        self.assertEqual(len(characters), 1)
        self.assertEqual(characters[0].name, "ValidChar")
        self.assertFalse(characters[0].is_narrator)
        self.assertTrue(characters[0].speaking)

        # Check that errors were printed for the skipped characters
        mock_print.assert_any_call("Skipping character at index 1 due to missing required key: 'speaking'. Data: {'name': 'MissingSpeaking', 'is_narrator': False, 'persona_description': 'Desc Invalid', 'text': 'Intro Invalid'}")
        mock_print.assert_any_call("Skipping character at index 2 due to missing required key: 'is_narrator'. Data: {'name': 'MissingNarratorFlag', 'speaking': True, 'persona_description': 'Desc Invalid 2', 'text': 'Intro Invalid 2'}")


    def test_identify_characters_malformed_json(self):
        """Test the case where the API returns invalid JSON."""
        self.mock_anthropic_client.create_message.return_value = "This is not JSON { characters: [}"
        input_text = "Another text."

        with patch('builtins.print') as mock_print:
            characters = self.service.identify_characters(input_text)

        self.mock_anthropic_client.create_message.assert_called_once()
        self.assertEqual(characters, [])
        # Check that the JSON parsing error was printed
        found_error_print = any("Failed to parse JSON response:" in call_args[0][0] for call_args in mock_print.call_args_list)
        self.assertTrue(found_error_print, "Expected JSON parsing error message was not printed.")

    def test_identify_characters_json_missing_characters_key(self):
        """Test the case where the JSON is valid but missing the 'characters' key."""
        mock_response_json = {"other_key": "value"}
        self.mock_anthropic_client.create_message.return_value = json.dumps(mock_response_json)
        input_text = "Text missing key."

        with patch('builtins.print') as mock_print:
            characters = self.service.identify_characters(input_text)

        self.mock_anthropic_client.create_message.assert_called_once()
        self.assertEqual(characters, [])
        # Check that the missing key error was printed
        mock_print.assert_any_call("Invalid or missing 'characters' key in response JSON.")

    def test_identify_characters_empty_characters_list(self):
        """Test the case where the API returns an empty character list."""
        mock_response_json = {"characters": []}
        self.mock_anthropic_client.create_message.return_value = json.dumps(mock_response_json)
        input_text = "No characters here."

        characters = self.service.identify_characters(input_text)

        self.mock_anthropic_client.create_message.assert_called_once()
        self.assertEqual(characters, [])

    def test_identify_characters_api_error(self):
        """Test the case where the client raises an exception."""
        self.mock_anthropic_client.create_message.side_effect = Exception("API connection failed")
        input_text = "This should fail."

        with patch('builtins.print') as mock_print:
            characters = self.service.identify_characters(input_text)

        self.mock_anthropic_client.create_message.assert_called_once()
        self.assertEqual(characters, [])
        # Check that the generic error was printed
        found_error_print = any("Error during character identification: API connection failed" in call_args[0][0] for call_args in mock_print.call_args_list)
        self.assertTrue(found_error_print, "Expected API error message was not printed.")

if __name__ == '__main__':
    unittest.main() 