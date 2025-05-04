"""
Narratix: A tool for analyzing text and generating audio narratives.
"""

__version__ = "0.1.0"

from narratix.core import (
    TextAnalyzer, 
    VoiceGenerator,
    AudioGenerator
)

__all__ = [
    'TextAnalyzer',
    'VoiceGenerator',
    'AudioGenerator'
]
