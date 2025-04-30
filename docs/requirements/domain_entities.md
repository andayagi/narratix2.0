# Domain Entity Specifications

This document outlines the core data structures (domain entities) for the Narratix application.

## 1. TextContent

- **Purpose:** Represents the input text to be processed.
- **Attributes:**
    - `content (str)`: The raw text content.
    - `language (str)`: Detected or specified language (e.g., 'en', 'es').
    - `metadata (dict)`: Optional metadata (source, author, etc.).
- **Methods:**
    - `segment()`: Logic to break text into processable chunks (sentences, paragraphs).
    - `validate()`: Check for invalid characters or excessive length.
- **Relationships:**
    - May be linked to multiple `NarrativeElement`s.

## 2. Character

- **Purpose:** Represents a distinct character voice within the text.
- **Attributes:**
    - `name (str)`: The name of the character (e.g., "Narrator", "Alice").
    - `description (str)`: Optional description of the character's persona or role.
- **Methods:**
    - `assign_voice(voice: Voice)`: Link a specific voice profile.
- **Relationships:**
    - Linked to one `Voice`.
    - Associated with specific `NarrativeElement`s where they speak.

## 3. Voice

- **Purpose:** Represents a specific Text-to-Speech (TTS) voice profile.
- **Attributes:**
    - `voice_id (str)`: Unique identifier provided by the TTS service (e.g., AWS Polly's "Joanna", Google's "en-US-Wavenet-F").
    - `voice_name (str)`: Human-readable name for the voice (e.g., "Joanna", "Wavenet-F").
    - `provider (str)`: The TTS provider (e.g., "AWS", "Google", "ElevenLabs").
    - `gender (str)`: e.g., "Male", "Female", "Neutral".
    - `accent (str)`: e.g., "US English", "British English".
    - `voice_description (str)`: Optional description provided by the service (e.g., "Child voice", "Newsreader style").
    - `pitch (float)`: Optional pitch adjustment.
- **Methods:**
    - `synthesize(text: str)`: (Likely handled by a service, but conceptually related).
- **Relationships:**
    - Can be linked to multiple `Character`s.

## 4. NarrativeElement

- **Purpose:** Represents a segment of the text assigned to a specific character or narrative role (e.g., a line of dialogue, a paragraph of narration).
- **Attributes:**
    - `element_id (UUID)`: Unique identifier for the element.
    - `text_segment (str)`: The actual text of this element.
    - `start_offset (int)`: Starting character position in the original `TextContent`.
    - `end_offset (int)`: Ending character position in the original `TextContent`.
    - `element_type (str)`: e.g., "dialogue", "narration", "scene_description".
    - `acting_instructions (str, optional)`: Natural language instructions for delivery (e.g., "speak excitedly", "whisper").
    - `speed (float, optional)`: Relative speaking rate adjustment (0.25=slower, 1.0=normal, 3.0=faster, non-linear scale). Defaults to 1.0.
    - `trailing_silence (float, optional)`: Duration of silence (in seconds) to add after this element. Defaults to 0.
- **Methods:**
    - `get_assigned_voice()`: Retrieve the voice associated via the Character.
- **Relationships:**
    - Linked to one `TextContent`.
    - Linked to one `Character` (or a default narrator).

## Data Validation Considerations

- **TextContent:** Max length, character encoding validation.
- **Character:** Name uniqueness within a context?
- **Voice:** Validation against available provider voices, valid pitch/rate ranges.
- **NarrativeElement:** Ensure offsets are valid and non-overlapping. Ensure `element_type` is from an allowed set. 