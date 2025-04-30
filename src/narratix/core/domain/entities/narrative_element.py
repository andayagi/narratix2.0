"""NarrativeElement entity representing a segment of text assigned to a specific character."""
from typing import Optional, Union
from uuid import UUID, uuid4


class NarrativeElement:
    """
    Represents a segment of text assigned to a specific character or narrative role.
    
    Examples include a line of dialogue, a paragraph of narration, or a scene description.
    Each element is linked to a specific part of the original text content and assigned
    to a character, which determines the voice used for synthesis.
    """
    
    VALID_ELEMENT_TYPES = {"dialogue", "narration", "scene_description"}
    
    def __init__(
        self,
        text_segment: str,
        character,  # Character object
        start_offset: int,
        end_offset: int,
        element_type: str = "narration",
        element_id: Optional[Union[UUID, str]] = None,
        acting_instructions: Optional[str] = None,
        speed: float = 1.0,
        trailing_silence: float = 0.0
    ):
        """
        Initialize a new NarrativeElement instance.
        
        Args:
            text_segment: The actual text of this element.
            character: The Character object associated with this element.
            start_offset: Starting character position in the original TextContent.
            end_offset: Ending character position in the original TextContent.
            element_type: Type of the element (e.g., "dialogue", "narration", "scene_description").
            element_id: Unique identifier for the element. If None, a new UUID is generated.
            acting_instructions: Natural language instructions for delivery 
                                (e.g., "speak excitedly", "whisper").
            speed: Relative speaking rate adjustment (0.25=slower, 1.0=normal, 3.0=faster).
            trailing_silence: Duration of silence (in seconds) to add after this element.
        """
        # Import Character here to avoid circular dependency
        from .character import Character
        
        if not isinstance(character, Character):
            raise TypeError("Expected a Character object")
            
        # Validate element_type
        if element_type not in self.VALID_ELEMENT_TYPES:
            raise ValueError(f"Invalid element_type. Must be one of: {', '.join(self.VALID_ELEMENT_TYPES)}")
            
        # Validate offsets
        if start_offset < 0 or end_offset < start_offset:
            raise ValueError("Invalid offset values")
            
        # Set properties
        self.element_id = element_id if element_id else uuid4()
        self.text_segment = text_segment
        self.character = character
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.element_type = element_type
        self.acting_instructions = acting_instructions
        self.speed = speed
        self.trailing_silence = trailing_silence
        
    def get_assigned_voice(self):
        """
        Retrieve the voice associated with this element via its Character.
        
        Returns:
            The Voice object linked to this element's character, or None if no voice is assigned.
        """
        return self.character.voice
        
    def __str__(self) -> str:
        """Return a string representation of the NarrativeElement."""
        return (f"NarrativeElement(id={self.element_id}, type={self.element_type}, "
                f"character={self.character.name}, length={len(self.text_segment)})") 