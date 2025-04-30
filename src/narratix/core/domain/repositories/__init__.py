"""Repository interfaces for domain entities."""

from .base_repository import BaseRepository
from .text_content_repository import TextContentRepository
from .character_repository import CharacterRepository
from .voice_repository import VoiceRepository
from .narrative_element_repository import NarrativeElementRepository

__all__ = [
    "BaseRepository",
    "TextContentRepository",
    "CharacterRepository",
    "VoiceRepository",
    "NarrativeElementRepository",
] 