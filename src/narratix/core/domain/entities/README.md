# Domain Entities

This package contains the core domain entities for the Narratix application. These entities represent the fundamental data structures and business objects in the application.

## Entities

### TextContent

Represents the input text to be processed. It contains the raw text content along with metadata and provides methods for validation and segmentation.

```python
from narratix.core.domain.entities import TextContent

# Create a new TextContent instance
text = TextContent(
    content="Once upon a time in a land far, far away...",
    language="en",
    metadata={"source": "fairy tale", "author": "Unknown"}
)

# Segment the text into processable chunks
segments = text.segment()
```

### Character

Represents a distinct character voice within the narrative text. Characters can be assigned voices and are associated with specific narrative elements.

```python
from narratix.core.domain.entities import Character, Voice

# Create a new Character
narrator = Character(
    name="Narrator",
    description="The main storyteller with a deep, authoritative voice"
)

# Assign a voice to the character
voice = Voice(voice_id="abc123", voice_name="Deep Voice", provider="AWS")
narrator.assign_voice(voice)
```

### Voice

Represents a specific Text-to-Speech (TTS) voice profile. This entity encapsulates the characteristics and settings of a TTS voice that can be assigned to characters.

```python
from narratix.core.domain.entities import Voice

# Create a new Voice
voice = Voice(
    voice_id="xyz789",
    voice_name="Female British",
    provider="ElevenLabs",
    gender="Female",
    accent="British English",
    voice_description="Professional newsreader voice",
    pitch=0.2
)
```

### NarrativeElement

Represents a segment of text assigned to a specific character or narrative role, such as a line of dialogue or a paragraph of narration.

```python
from narratix.core.domain.entities import NarrativeElement, Character

# Create a character
alice = Character(name="Alice")

# Create a narrative element
dialogue = NarrativeElement(
    text_segment="Hello, world!",
    character=alice,
    start_offset=0,
    end_offset=13,
    element_type="dialogue",
    acting_instructions="speak excitedly",
    speed=1.2,
    trailing_silence=0.5
)
```

## Validation

Each entity includes validation logic to ensure data integrity:

- **TextContent**: Validates text is not empty and doesn't exceed maximum length
- **Character**: No specific validation currently
- **Voice**: No specific validation currently
- **NarrativeElement**: Validates element type is from allowed set and offsets are valid

## Relationships

- A **TextContent** can be linked to multiple **NarrativeElement** instances
- A **Character** is linked to one **Voice** and associated with specific **NarrativeElement** instances
- A **Voice** can be linked to multiple **Character** instances
- A **NarrativeElement** is linked to one **Character** and indirectly to one **Voice** through that character 