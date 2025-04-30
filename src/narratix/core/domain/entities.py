from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Character:
    name: str
    # Future fields like description, aliases, etc. can be added later.


@dataclass
class TextSegment:
    segment_type: str  # e.g., "dialogue", "narration", "action"
    content: str
    characters: Optional[List[Character]] = None # Characters present in this segment
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None


@dataclass
class AnalyzedText:
    original_text: str
    segments: List[TextSegment]
    characters: List[Character] 