"""Character entity representing a distinct voice within the text."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Character:
    """
    Represents a distinct character voice within the narrative text.
    """
    name: str
    is_narrator: bool = False
    speaking: bool = False
    persona_description: Optional[str] = None
    text: Optional[str] = None

    def __str__(self) -> str:
        """Return a string representation of the Character."""
        return f"Character(name={self.name}, is_narrator={self.is_narrator}, speaking={self.speaking})" 