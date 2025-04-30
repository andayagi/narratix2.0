from abc import ABC, abstractmethod
from typing import List

from .entities import Character


class CharacterIdentificationService(ABC):
    """Interface for identifying characters in a given text."""

    @abstractmethod
    def identify_characters(self, text: str) -> List[Character]:
        """Identifies characters mentioned in the provided text.

        Args:
            text: The input text to analyze.

        Returns:
            A list of identified Character objects.
        """
        pass


# Add other service interfaces here as needed (e.g., TextSegmentationService) 