# Sequence Diagram Example: Processing a Text Snippet via CLI

This diagram illustrates the typical flow when a user processes a text snippet using the Command Line Interface (CLI).

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Core
    participant TextParser
    participant CharacterManager
    participant VoiceMapper
    participant TTSService
    participant OutputHandler

    User->>CLI: narratix process --input text.txt --output audio.mp3
    CLI->>Core: process_text(input_path, output_path)
    Core->>TextParser: parse(input_content)
    TextParser-->>Core: parsed_elements (e.g., dialogue lines, narration)
    Core->>CharacterManager: identify_characters(parsed_elements)
    CharacterManager-->>Core: characters_with_lines
    Core->>VoiceMapper: assign_voices(characters_with_lines)
    VoiceMapper-->>Core: lines_with_voices
    loop For each line/segment
        Core->>TTSService: synthesize(text, voice_config)
        TTSService-->>Core: audio_chunk
        Core->>OutputHandler: append_chunk(audio_chunk)
    end
    Core->>OutputHandler: finalize_output(output_path)
    OutputHandler-->>Core: success
    Core-->>CLI: processing_complete
    CLI-->>User: Output saved to audio.mp3

```

**Description:**

1.  The User invokes the `narratix` CLI command.
2.  The CLI parses arguments and calls the main processing function in the Core module.
3.  The Core orchestrates the process: parsing text, identifying characters, assigning voices.
4.  For each segment needing audio, the Core calls the TTS Service.
5.  Audio chunks are assembled by the Output Handler.
6.  Finally, the complete audio file is saved, and the user is notified. 