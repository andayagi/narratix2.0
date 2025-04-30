import json
from typing import List, Dict, Any
import re
import logging # Added logging import

# Standardized import using src prefix
from src.narratix.core.domain.entities import Character
from src.narratix.core.domain.interfaces import CharacterIdentificationService
# Placeholder import - Assumes AnthropicClient is defined in this path as per Task 1
# Standardized import using src prefix
from src.narratix.infrastructure.external.anthropic import AnthropicClient


class AnthropicCharacterIdentificationService(CharacterIdentificationService):
    """Implementation of CharacterIdentificationService using Anthropic's Claude API."""

    # Detailed prompt template based on user input
    _PROMPT_MESSAGES_TEMPLATE = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "<examples>\\n<example>\\n<text>\\n\"Maya soared through the crimson sky on Azura's massive scaled back. 'We need to fly higher to avoid the storm clouds,' she called out, her voice determined yet concerned. 'Always so cautious,' laughed Kell from his perch on the nearby cliff. 'Your dragon can handle a little lightning!' His tone was teasing but affectionate. Maya frowned. 'I'm not risking Azura's wings again,' she replied firmly.\"\\n</text>\\n<ideal_output>\\n{\\n  \"characters\": [\\n    {\\n      \"name\": \"Narrator\",\\n      \"is_narrator\": true,\\n      \"speaking\":false,\\n      \"persona_description\": \"Adult male, American accent, has the charismatic voice of a seasoned fantasy audiobook narrator, with a deep, resonant tone and a talent for dramatic pacing that brings every battle scene to life.\",\\n      \"text\": \"Welcome to this book, it's a fantasy romance taking place in a magical world of dragons and riders\\n    },\\n    {\\n      \"name\": \"Maya\",\\n      \"is_narrator\": false,\\n      \"speaking\":true,\\n      \"persona_description\": \"Adult female, American accent, has an intense, focused voice, like a weathered astronaut recounting a harrowing mission with controlled emotion and steely determination.\",\\n      \"text\": \"Hi, I'm Maya and this is my dragon Azura\"\\n    },\\n    {\\n      \"name\": \"Kell\",\\n      \"is_narrator\": false,\\n      \"speaking\":true,\\n      \"persona_description\": \"Adult male, American accent, has the charismatic, expressive voice of a mischievous extreme sports guru, who is both playful and warm\",\\n       \"text\": \"Hi, I'm Kell and I'm an experienced dragon rider\"\\n    }\\n  ]\\n}\\n</ideal_output>\\n</example>\\n<example>\\n<text>\\n\"I soared through the crimson sky on Azura's massive scaled back. 'We need to fly higher to avoid the storm clouds,' I called out, my voice determined yet concerned. 'Always so cautious,' laughed Kell from his perch on the nearby cliff. 'Your dragon can handle a little lightning!' His tone was teasing but affectionate. I frowned. 'I'm not risking Azura's wings again,' I replied firmly.\"\\n</text>\\n<ideal_output>\\n{\\n  \"characters\": [\\n    {\\n      \"name\": \"protagonist\",\\n      \"is_narrator\": true,\\n      \"speaking\":true,\\n      \"persona_description\": \"Adult female, American accent, has an emotive voice, with a medium-high pitch that effortlessly conveys a wide range of feelings, making her an amazing voice for animation and heartfelt stories.\",\\n       \"text\": \"I'm a dragon rider and this is my dragon Azura\"\\n    },\\n    {\\n      \"name\": \"Kell\",\\n      \"is_narrator\": false,\\n      \"speaking\":true,\\n      \"persona_description\": \"Adult male, American accent, charismatic, expressive voice of a mischievous extreme sports guru, who speaks with a playful yet warm American accent, inspiring and thrilling listeners with every word\",\\n       \"text\": \"I'm Kell and I'm an experienced dragon rider\"\\n    }\\n  ]\\n}\\n</ideal_output>\\n</example>\\n</examples>\\n\\n"
                },
                {
                    "type": "text",
                    "text": "Analyze text only for characters with dialogue parts and output only json file. \\n\\nOutput Format:\\nProvide your analysis in the following JSON format:\\n{{\\n  \"characters\": [\\n    {{\\n      \"name\": \"Character name or Narrator\",\\n      \"is_narrator\": true/false,\\n      \"speaking\":true,\\n      \"persona_description\": \"Age group, male OR female, short voice\\\\persona\\\\genre description\",\\n      \"text\":\"how the character would introduce itself to others in the book, if third person narrator then an introduction to the book\"\\n    }},\\n    {{\\n      \"name\": \"Another character\",\\n      \"is_narrator\": false,\\n      \"speaking\":true,\\n      \"persona_description\": \"Age group, male OR female, short voice\\\\persona\\\\genre description\",\\n      \"text\":\"how the character would introduce itself to others in the book\"\\n    }}\\n  ]\\n}}\\n\\n\\nInstructions:\\n1. Identify all characters in the text\\n2. If the text uses third-person narration, add a \"Narrator\" record\\n3. IMPORTANT: For first-person narratives, do not create both a \"protagonist\" and a separate \"Narrator\" role - they are the same character.\\n4. For each character add if it speaks in the text speaking=true\\\\false\\n5. For each entry describe in one short sentence the voice for voiceover - [AGE GROUP] [MALE or FEMALE], American accent, [CORE VOCAL QUALITY + INTENSITY LEVEL] voice, [SPEAKING PATTERN], like [PRECISE CHARACTER ARCHETYPE] [PERFORMING CHARACTERISTIC ACTION WITH EMOTIONAL SUBTEXT]. words like young and youthful should be used only for children characters. \\n6. For each entry describe how the character would introduce itself to others in the book, if third person narrator then an introduction to the book\\n\\n\\nNow analyze this text:\\n{{text}}"
                }
            ]
        }
    ]
    _MAX_TOKENS = 8192 # As specified in the example prompt
    _TEMPERATURE = 1.0 # As specified in the example prompt
    _MODEL = "claude-3-5-haiku-20241022" # As specified in the example prompt

    def __init__(self, client: AnthropicClient):
        """Initializes the service with an AnthropicClient instance."""
        self._client = client
        self.logger = logging.getLogger(__name__) # Initialize logger

    def identify_characters(self, text: str) -> List[Character]:
        """Identifies characters using the Anthropic API with detailed JSON output.

        Args:
            text: The input text to analyze.

        Returns:
            A list of identified Character objects with detailed attributes.
            Returns an empty list if the API call fails, no characters are found,
            or parsing fails.
        """
        # Deep copy the template to avoid modifying it in place
        messages = json.loads(json.dumps(self._PROMPT_MESSAGES_TEMPLATE))

        # Inject the actual text into the last message content part
        # Find the correct part to inject the text (assuming it's the last 'text' type content in the last message)
        if messages and messages[-1].get("content"):
            for content_part in reversed(messages[-1]["content"]):
                if content_part.get("type") == "text" and "{{text}}" in content_part["text"]:
                    content_part["text"] = content_part["text"].replace("{{text}}", text)
                    break

        try:
            # Log request details at DEBUG level
            self.logger.debug(
                "Anthropic Request for Character ID: Model=%s, MaxTokens=%s, Temp=%s, Messages=%s",
                self._MODEL, self._MAX_TOKENS, self._TEMPERATURE, json.dumps(messages, indent=2)
            )

            response_content = self._client.generate_completion(
                model=self._MODEL,
                max_tokens=self._MAX_TOKENS,
                temperature=self._TEMPERATURE,
                messages=messages
            )

            # Log full raw response at DEBUG level
            self.logger.debug("Anthropic Raw Response for Character ID: %s", response_content)

            if not response_content:
                # Use logger for warnings/errors too
                self.logger.warning("Anthropic response was empty.")
                return []

            # Parse the JSON response
            # The actual response structure from the client might vary,
            # e.g., response_content might be a string needing json.loads,
            # or it might be an object with attributes like response.content[0].text
            # Adjust parsing based on the actual client implementation.
            # Assuming response_content is the JSON string:
            try:
                # Find the JSON block within the response text if necessary
                json_match = re.search(r'```json\\n({.*?})\\n```', response_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                     # Attempt to parse the whole response if no ```json ``` block found
                    json_str = response_content.strip()

                response_data = json.loads(json_str)

            except json.JSONDecodeError as json_e:
                 # Log error
                 self.logger.error("Failed to parse JSON response: %s", json_e)
                 self.logger.error("Received response content: %s", response_content)
                 return []


            if "characters" not in response_data or not isinstance(response_data["characters"], list):
                # Log warning
                self.logger.warning("Invalid or missing 'characters' key in response JSON: %s", response_data)
                return []

            characters = []
            for i, char_data in enumerate(response_data["characters"]):
                try:
                    # Validate required fields exist before creating the object
                    name = char_data["name"]
                    is_narrator = char_data["is_narrator"] # Direct access, will raise KeyError if missing
                    speaking = char_data["speaking"] # Direct access, will raise KeyError if missing

                    # Optional fields with .get()
                    persona_description = char_data.get("persona_description")
                    intro_text = char_data.get("text")

                    characters.append(Character(
                        name=name,
                        is_narrator=is_narrator,
                        speaking=speaking,
                        persona_description=persona_description,
                        text=intro_text
                    ))
                except KeyError as key_e:
                    # Log warning
                    self.logger.warning("Skipping character at index %d due to missing required key: %s. Data: %s", i, key_e, char_data)
                    continue # Skip this character and proceed to the next
                except Exception as e:
                    # Catch other potential errors during character processing
                    # Log error
                    self.logger.error("Error processing character at index %d: %s. Data: %s", i, e, char_data)
                    continue # Skip this character

            return characters

        except Exception as e:
            # Basic error handling - log the error or handle more gracefully
            # Log error
            self.logger.error("Error during character identification: %s", e, exc_info=True) # Include traceback
            # print(f"Error during character identification: {e}")
            # Consider logging the exception details: import traceback; traceback.print_exc()
            return [] # Return empty list on failure 