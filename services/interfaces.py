"""
Service Interface Contracts

This module defines Protocol interfaces and abstract base classes for the Narratix 2.0 service layer.
These contracts enable better testing through dependency injection and provide clear service boundaries.
"""

from typing import Protocol, List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session


# Text Analysis Service Interface
class TextAnalysisService(Protocol):
    """Protocol for text analysis and character extraction services."""
    
    async def analyze_characters(self, text: str) -> List[Dict[str, Any]]:
        """Extract characters from text with descriptions and dialogue patterns."""
        ...
    
    async def segment_text(self, text: str, characters: List[Dict]) -> List[Dict]:
        """Segment text by character dialogue and narration."""
        ...
    
    async def process_text_analysis(self, text_id: int, force_reanalyze: bool = False) -> Dict[str, Any]:
        """Complete text analysis pipeline for a given text."""
        ...


# Voice Generation Service Interface  
class VoiceGenerationService(Protocol):
    """Protocol for character voice generation services."""
    
    async def generate_character_voice(
        self, 
        character_id: int,
        character_name: str,
        character_description: str,
        character_intro_text: str,
        text_id: int,
        force_regenerate: bool = False
    ) -> Optional[str]:
        """Generate voice for a single character."""
        ...
    
    async def generate_all_character_voices_parallel(self, text_id: int) -> List[str]:
        """Generate voices for all characters in parallel."""
        ...


# Speech Generation Service Interface
class SpeechGenerationService(Protocol):
    """Protocol for text-to-speech conversion services."""
    
    async def generate_text_audio(
        self,
        text_id: int,
        batch_size: int = 5,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """Generate speech audio for all text segments."""
        ...
    
    async def process_batch(
        self,
        segments: List[Any], 
        text_id: int,
        force_regenerate: bool = False
    ) -> Tuple[int, int]:
        """Process a batch of text segments for speech generation."""
        ...


# Background Music Service Interface
class BackgroundMusicService(Protocol):
    """Protocol for background music generation services."""
    
    async def update_text_with_music_prompt(self, text_id: int) -> Optional[str]:
        """Analyze text and generate music generation prompt."""
        ...
    
    async def generate_background_music(self, text_id: int) -> Optional[str]:
        """Generate background music for text."""
        ...


# Sound Effects Service Interface
class SoundEffectsService(Protocol):
    """Protocol for sound effects generation services."""
    
    async def analyze_sound_effects_for_text(self, text_id: int) -> List[Dict[str, Any]]:
        """Analyze text for sound effect opportunities."""
        ...
    
    async def generate_sound_effects_for_text(self, text_id: int) -> Dict[str, Any]:
        """Generate sound effects for analyzed text."""
        ...


# Audio Analysis Service Interface
class AudioAnalysisService(Protocol):
    """Protocol for audio analysis services."""
    
    async def analyze_text_for_audio(self, text_id: int) -> Dict[str, Any]:
        """Analyze text for audio generation requirements."""
        ...
    
    async def process_audio_analysis_for_text(self, text_id: int) -> Dict[str, Any]:
        """Process complete audio analysis pipeline."""
        ...


# Audio Export Service Interface
class AudioExportService(Protocol):
    """Protocol for audio combination and export services."""
    
    async def combine_speech_segments(
        self,
        text_id: int,
        include_background_music: bool = True,
        include_sound_effects: bool = True,
        normalize_audio: bool = True
    ) -> Optional[str]:
        """Combine speech segments with background audio."""
        ...
    
    async def export_final_audio(
        self,
        text_id: int,
        format: str = "mp3",
        force_alignment: bool = False
    ) -> Dict[str, Any]:
        """Export final combined audio with optional force alignment."""
        ...


# Abstract Base Service Class
class BaseService(ABC):
    """Abstract base class providing common service patterns."""
    
    def __init__(self, logger=None):
        self.logger = logger or self._get_default_logger()
    
    @abstractmethod
    def _get_default_logger(self):
        """Get default logger for the service."""
        pass
    
    async def _handle_api_error(self, error: Exception, operation: str) -> None:
        """Standard error handling for API operations."""
        self.logger.error(f"Error in {operation}: {str(error)}")
        raise error
    
    async def _retry_with_backoff(
        self, 
        operation,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        *args,
        **kwargs
    ):
        """Execute operation with exponential backoff retry."""
        import asyncio
        
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = backoff_factor ** attempt
                    self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"All {max_retries + 1} attempts failed: {str(e)}")
                    raise last_exception


# Client Factory Interface
class ClientFactoryService(Protocol):
    """Protocol for external API client factory."""
    
    @classmethod
    def get_anthropic_client(cls):
        """Get Anthropic sync client."""
        ...
    
    @classmethod  
    def get_anthropic_async_client(cls):
        """Get Anthropic async client."""
        ...
    
    @classmethod
    def get_hume_async_client(cls):
        """Get Hume async client."""
        ...
    
    @classmethod
    def get_hume_sync_client(cls):
        """Get Hume sync client."""
        ...
    
    @classmethod
    def get_replicate_client(cls):
        """Get Replicate client."""
        ...


# Database Session Manager Interface
class DatabaseSessionManager(Protocol):
    """Protocol for database session management."""
    
    def __call__(self):
        """Context manager that yields database session with automatic cleanup."""
        ...


# Webhook Processing Service Interface
class WebhookProcessingService(Protocol):
    """Protocol for webhook processing services."""
    
    async def process_webhook(
        self,
        webhook_data: Dict[str, Any],
        webhook_type: str
    ) -> Dict[str, Any]:
        """Process incoming webhook data."""
        ...
    
    async def handle_completion(
        self,
        operation_id: str,
        result_data: Dict[str, Any]
    ) -> bool:
        """Handle completion of async operation."""
        ...