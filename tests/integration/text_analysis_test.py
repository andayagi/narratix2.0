import pytest
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any
import json
import os  # Added for environment variable access

# Assuming paths are correct relative to the project root
from src.narratix.core.domain.entities.character import Character
# Import the concrete implementation and the real client
from src.narratix.services.character_identification import AnthropicCharacterIdentificationService
from src.narratix.infrastructure.external.anthropic import AnthropicClient

# We might need TextContent if the service expects it, let's assume simple text for now
# from src.narratix.core.domain.entities.text_content import TextContent


# Realistic text example (can be expanded later)
REALISTIC_TEXT_EXAMPLE = """
The old man sighed, adjusting his spectacles. "It's been a long journey," he rasped, his voice thin as paper.
Elara watched him, her brow furrowed. "Do you think we'll find it?"
"Hope is all we have left," a third voice interjected, smooth and low. It was Kaelen, leaning against the doorframe.
The Narrator observed the scene, noting the tension.
"""

# Expected simulated Claude response for the realistic text
# This needs to be carefully crafted based on the prompt template used in CharacterIdentificationService
# and should match the attributes defined in the Character entity.
EXPECTED_CLAUDE_RESPONSE_JSON = {
    "characters": [
        {
            "name": "Old Man",
            "is_narrator": False,
            "speaking": True,
            "persona_description": "Elderly, weary, raspy voice, reflective.",
            "text": "It's been a long journey,"
        },
        {
            "name": "Elara",
            "is_narrator": False,
            "speaking": True,
            "persona_description": "Concerned, questioning.",
            "text": "Do you think we'll find it?"
        },
        {
            "name": "Kaelen",
            "is_narrator": False,
            "speaking": True,
            "persona_description": "Smooth voice, observant, possibly cynical.",
            "text": "Hope is all we have left,"
        },
         {
            "name": "Narrator",
            "is_narrator": True,
            "speaking": False,
            "persona_description": "Observational, objective.",
            "text": "The Narrator observed the scene, noting the tension."
        }
    ]
}

# Expected list of Character objects corresponding to the JSON response
EXPECTED_CHARACTERS = [
    Character(name="Old Man", is_narrator=False, speaking=True, persona_description="Elderly, weary, raspy voice, reflective.", text="It's been a long journey,"),
    Character(name="Elara", is_narrator=False, speaking=True, persona_description="Concerned, questioning.", text="Do you think we'll find it?"),
    Character(name="Kaelen", is_narrator=False, speaking=True, persona_description="Smooth voice, observant, possibly cynical.", text="Hope is all we have left,"),
    Character(name="Narrator", is_narrator=True, speaking=False, persona_description="Observational, objective.", text="The Narrator observed the scene, noting the tension.")
]


# Mock the AnthropicClient dependency
@patch('src.narratix.services.character_identification.AnthropicClient')
def test_character_identification_with_realistic_text(MockAnthropicClient):
    """
    Tests the CharacterIdentificationService with a more realistic text snippet
    and simulated Claude response.
    """
    # Configure the mock AnthropicClient instance and its methods
    mock_anthropic_instance = MockAnthropicClient.return_value
    # Simulate the behavior of create_message to return our predefined JSON string
    # The service expects a string response to parse, potentially with JSON inside
    # Let's provide the raw JSON string first.
    mock_anthropic_instance.create_message.return_value = json.dumps(EXPECTED_CLAUDE_RESPONSE_JSON)

    # Instantiate the service (it will receive the mocked client)
    # We might need to pass config or other dependencies if the constructor requires them
    # Correctly instantiate the concrete service class
    character_service = AnthropicCharacterIdentificationService(client=mock_anthropic_instance)

    # Call the method under test
    # Assuming the method takes the raw text string directly
    identified_characters = character_service.identify_characters(REALISTIC_TEXT_EXAMPLE)

    # Assertions
    # Verify create_message was called
    mock_anthropic_instance.create_message.assert_called_once()
    # Add more specific call assertions if needed (e.g., check the prompt)

    # Compare the identified characters with the expected list
    # Ensure the comparison handles potential ordering differences if necessary
    assert len(identified_characters) == len(EXPECTED_CHARACTERS), "Incorrect number of characters identified"

    # Detailed comparison (might need a helper function or careful sorting if order isn't guaranteed)
    # For simplicity, assuming order is preserved or comparing sets/using detailed loops
    for expected, actual in zip(sorted(EXPECTED_CHARACTERS, key=lambda c: c.name), sorted(identified_characters, key=lambda c: c.name)):
         assert expected.name == actual.name
         assert expected.is_narrator == actual.is_narrator
         assert expected.speaking == actual.speaking
         assert expected.persona_description == actual.persona_description
         # Text comparison might need refinement (e.g., exact match vs. containment)
         assert expected.text == actual.text


# Mark for tests requiring external resources/API calls
integration_test = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="Requires ANTHROPIC_API_KEY environment variable"
)

@integration_test
def test_character_identification_real_api_call():
    """
    Tests the CharacterIdentificationService with a real Anthropic API call.
    Requires the ANTHROPIC_API_KEY environment variable to be set.
    """
    # Instantiate the real client (implicitly uses API key from env var)
    try:
        anthropic_client = AnthropicClient() # Assumes constructor handles API key loading
    except Exception as e: # Catch potential errors during client init (e.g., missing key despite env var check)
        pytest.fail(f"Failed to initialize AnthropicClient: {e}")

    # Instantiate the service with the real client
    character_service = AnthropicCharacterIdentificationService(client=anthropic_client)

    # Call the method under test
    try:
        identified_characters = character_service.identify_characters(REALISTIC_TEXT_EXAMPLE)
    except Exception as e: # Catch errors during the API call itself
        pytest.fail(f"Anthropic API call failed: {e}")

    # Assertions (more flexible than mocked test)
    assert isinstance(identified_characters, list), "Result should be a list"
    assert len(identified_characters) > 0, "Should identify at least one character"

    # Check if all expected characters are roughly identified (by name)
    expected_names = {"Old Man", "Elara", "Kaelen", "Narrator"}
    identified_names = {char.name for char in identified_characters}

    # Allow for potential variations (e.g., "The Old Man" vs "Old Man")
    # This basic check verifies the core names are found. More robust checks might
    # involve fuzzy matching or checking for inclusion.
    missing_names = expected_names - identified_names
    # Allow Narrator to be sometimes missed or named differently by the model
    missing_names -= {"Narrator"} # Be more lenient about Narrator detection in real calls
    assert not missing_names, f"Expected characters not found: {missing_names}"


    # Basic type checks on the first identified character (if any)
    if identified_characters:
        char = identified_characters[0]
        assert isinstance(char, Character)
        assert isinstance(char.name, str)
        assert isinstance(char.is_narrator, bool)
        assert isinstance(char.speaking, bool)
        assert isinstance(char.persona_description, str)
        assert isinstance(char.text, str) # Or check if it's None/str depending on expected behavior

    # Optional: Spot-check a specific character if identification is reliable enough
    # e.g., find the Narrator and check is_narrator flag
    narrator_chars = [c for c in identified_characters if "narrator" in c.name.lower()]
    if narrator_chars:
         assert narrator_chars[0].is_narrator is True, "Identified Narrator should have is_narrator=True"
    # else:
        # Warn or log if Narrator wasn't found, but don't fail the test strictly
        # print("Warning: Narrator character not explicitly identified in real API call.")


# Placeholder for potential future tests or setup
def setup_module(module):
    """ setup any state specific to the execution of the given module."""
    pass

def teardown_module(module):
    """ teardown any state that was previously setup with a setup_module
    method.
    """
    pass 