from typing import Optional

class HumeProvider:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key 