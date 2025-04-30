import os
import logging
import anthropic
from anthropic.types import MessageParam, Message
from typing import List, Dict, Any, Union

class AnthropicClient:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.logger = logging.getLogger(__name__)

    def generate_completion(
        self, 
        messages: List[Dict[str, Any]],
        model: str = "claude-3-opus-20240229",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """
        Generate a completion using Anthropic's Messages API.
        
        Args:
            messages: A list of message objects (dicts) conforming to the Anthropic Messages API schema.
            model: The Anthropic model to use.
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature.
            
        Returns:
            The generated text response content.
            
        Raises:
            Exception: If there's an error communicating with the Anthropic API.
        """
        try:
            response: Message = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages
            )
            if response.content and isinstance(response.content, list) and len(response.content) > 0:
                if hasattr(response.content[0], 'text'):
                    return response.content[0].text
                else:
                    self.logger.warning("First content block in Anthropic response has no 'text' attribute.")
                    return ""
            else:
                self.logger.warning("Anthropic response content is empty or not in expected format.")
                return ""

        except anthropic.APIError as e:
            self.logger.error(f"Anthropic API error: {str(e)}")
            raise Exception(f"Error communicating with Anthropic API: {str(e)}")
        except anthropic.RateLimitError as e:
            self.logger.error(f"Rate limit exceeded: {str(e)}")
            raise Exception(f"Anthropic rate limit exceeded: {str(e)}")
        except anthropic.APIConnectionError as e:
            self.logger.error(f"Connection error: {str(e)}")
            raise Exception(f"Connection error with Anthropic API: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise Exception(f"Unexpected error during Anthropic API call: {str(e)}") 