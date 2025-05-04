from typing import Optional

class AnthropicProvider:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key 