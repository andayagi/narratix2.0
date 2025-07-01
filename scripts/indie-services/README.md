# CLI Wrappers - Service Interface Scripts

This folder contains thin CLI wrappers that provide command-line interfaces to the core services located in `services/`. These scripts call service functions directly without duplicating logic.

**Architecture**: CLI wrapper → Service function call → Database operation  
**Benefit**: Single source of truth for all service logic in `services/`

## Audio Analysis

**Script:** `audio_analysis_standalone.py`

CLI wrapper for the audio analysis service that analyzes text for audio elements.

### Usage:

```bash
# Analyze text for audio elements by ID
python3 scripts/indie-services/audio_analysis_standalone.py --text_id 123
```

### What it calls:
- **Service function**: `services.audio_analysis.analyze_text_for_audio(text_id)`

### What the service does:
1. **Cleanup**: Removes all existing audio-related data for the text_id:
   - Deletes existing sound effect records
   - Clears background_music_prompt field
   - Clears background_music_audio_b64 field

2. **Analysis**: Runs unified Claude analysis for both:
   - Soundscape generation (atmospheric background music description)
   - Sound effects identification (specific audio events with timing)

3. **Storage**: Saves results to database:
   - Stores soundscape as background_music_prompt
   - Creates sound effect records with word positions and prompts
   - Applies text length filtering (max 1 effect per 700 characters)
   - Ranks effects by importance

### Requirements:
- Database connection configured
- Anthropic API key set in environment
- Text must exist in database

### Output:
The script provides detailed logging and a summary including:
- Content length and text ID
- Soundscape generation status and prompt
- Number of sound effects created with details
- Word positions and ranking for each effect

## Text Analysis

**Script:** `text_analysis_standalone.py`

CLI wrapper for the text analysis service that processes text content and creates character and segment data.

### Usage:

```bash
# Analyze existing text by ID
python3 scripts/indie-services/text_analysis_standalone.py --text-id 123

# Analyze text from file and create new database record
python3 scripts/indie-services/text_analysis_standalone.py --file scripts/input_interactive_e2e.txt --create-text

# Use default file (scripts/input_interactive_e2e.txt) and create new record
python3 scripts/indie-services/text_analysis_standalone.py --create-text
```

### What it calls:
- **Service function**: `services.text_analysis.process_text_analysis(text_id)`

### What the service does:
1. **Cleanup**: Deletes all existing data for the text_id:
   - Removes Hume AI voices 
   - Clears character voice provider IDs
   - Deletes existing segments and characters from database

2. **Analysis**: Runs two-phase text analysis:
   - Phase 1: Character identification using Claude Haiku
   - Phase 2: Text segmentation and voice instructions using Claude Sonnet

3. **Storage**: Saves results to database:
   - Creates character records with voice descriptions
   - Creates text segments with acting instructions
   - Marks text as analyzed

### Requirements:
- Database connection configured
- Anthropic API key set in environment
- Hume API key set in environment (for voice cleanup)

### Output:
The script provides detailed logging and a summary of results including:
- Number of characters created
- Number of segments created
- Text analysis completion status

## Sound Effects

**Script:** `sound_effects_standalone.py`

CLI wrapper for the sound effects service that generates audio for existing sound effect records.

### Usage:

```bash
# Generate audio for existing sound effects 
python3 scripts/indie-services/sound_effects_standalone.py --text-id 123

# Use parallel processing for faster generation
python3 scripts/indie-services/sound_effects_standalone.py --text-id 123 --parallel

# Automatically start FastAPI server if not running
python3 scripts/indie-services/sound_effects_standalone.py --text-id 123 --auto-start-server

# Skip server health check (advanced users)
python3 scripts/indie-services/sound_effects_standalone.py --text-id 123 --skip-server-check
```

### What it calls:
- **Service function**: `services.sound_effects.generate_sound_effects_for_text(text_id)`

### What the service does:
1. **Server Check**: Ensures FastAPI server is running:
   - Checks if webhook endpoint is available
   - Can automatically start server if needed (with `--auto-start-server`)
   - Offers interactive options to start server or continue without it

2. **Validation**: Checks that sound effect records with prompts exist:
   - Returns error if no sound effects found for text_id
   - Returns error if sound effects exist but have no prompts

3. **Cleanup**: Clears existing audio data:
   - Removes audio_data_b64 values from sound effect records
   - Keeps all other sound effect data intact

4. **Generation**: Creates audio using Replicate webhooks:
   - Uses existing prompts from database records
   - Triggers AI audio generation via stable-audio model
   - Processes generation asynchronously via webhooks

### Requirements:
- Database connection configured
- Existing sound effect records with prompts (run text analysis first)
- Replicate API key set in environment
- Webhook endpoints configured for async processing

### Output:
The script provides detailed logging and a summary including:
- Number of sound effects processed
- Audio generation status (webhook-based, asynchronous)
- Effect details (name, prompt, word positions, duration, rank)

## Background Music Generation

**Script:** `background_music_standalone.py`

CLI wrapper for the background music service that generates background music for a specific text.

**Usage:**
```bash
python scripts/indie-services/background_music_standalone.py --text_id <ID>
```

**Options:**
- `--text_id`: ID of the text to generate background music for (required)
- `--timeout`: Timeout in seconds to wait for webhook response (default: 300)
- `--poll_interval`: Polling interval in seconds (default: 10)

**Example:**
```bash
# Generate background music for text ID 34
python scripts/indie-services/background_music_standalone.py --text_id 34

# With custom timeout and polling
python scripts/indie-services/background_music_standalone.py --text_id 34 --timeout 600 --poll_interval 15
```

### What it calls:
- **Service function**: `services.background_music.generate_background_music(text_id)`

**Process:**
1. Checks if text exists and has existing prompt/audio
2. Deletes existing audio if present
3. Generates background music prompt if needed (using unified audio analysis)
4. Triggers Replicate webhook for music generation
5. Polls database waiting for webhook response (typically 2-3 minutes)
6. Confirms audio is stored in database

**Requirements:**
- Text must exist in database
- Replicate API key configured
- Webhook endpoint accessible for Replicate callbacks

## Speech Generation

**Script:** `speech_generation.py`

CLI wrapper for the speech generation service that generates speech audio for all segments of a text.

### Usage:

```bash
# Generate speech for existing text segments
python3 scripts/indie-services/speech_generation.py --text_id 123
```

### What it calls:
- **Service function**: `services.speech_generation.generate_text_audio(text_id)`

### What the service does:
1. **Validation**: Checks prerequisites for speech generation:
   - Verifies text exists in database
   - Confirms segments exist (requires text analysis to be run first)
   - Validates characters have voice assignments (requires voice generation to be run first)

2. **Cleanup**: Clears existing audio data:
   - Removes audio_data_b64 from all segments for the text_id
   - Keeps all other segment data intact

3. **Generation**: Creates speech audio using Hume API:
   - Uses parallel batch processing for efficiency
   - Maintains narrative coherence with continuation context
   - Handles retry logic for failed generations
   - Stores base64 encoded audio data in database

4. **Storage**: Saves results to database:
   - Updates segment records with audio_data_b64
   - Invalidates existing force alignment data (if present)
   - Provides detailed progress logging

### Requirements:
- Database connection configured
- Hume API key set in environment
- Text must be analyzed first (segments and characters must exist)
- Characters must have voice provider IDs assigned (voice generation must be run first)

### Output:
The script provides detailed logging and a summary of results including:
- Number of segments processed
- Number of segments with generated audio
- Number of previously cleared audio segments
- Speech generation completion status

## Voice Generation

**Script:** `voice_generation.py`

CLI wrapper for the voice generation service that assigns AI voices to all characters.

### Usage:

```bash
# Generate voices for all characters
python3 scripts/indie-services/voice_generation.py --text_id 123
```

### What it calls:
- **Service function**: `services.voice_generation.generate_all_character_voices_parallel(text_id)`

### What the service does:
1. **Voice Assignment**: Creates unique AI voices for all characters using Hume API
2. **Parallel Processing**: Generates multiple voices concurrently for efficiency
3. **Database Storage**: Stores voice provider IDs for each character

## Combine Export Audio

**Script:** `combine_export_audio_standalone.py`

CLI wrapper for the audio export service that combines speech segments and exports final audio.

### Usage:

```bash
# Basic usage - exports final audio with all available components
python3 scripts/indie-services/combine_export_audio_standalone.py --text_id 123

# Specify custom output directory
python3 scripts/indie-services/combine_export_audio_standalone.py --text_id 123 --output_dir /path/to/output

# Advanced options with custom audio settings
python3 scripts/indie-services/combine_export_audio_standalone.py --text_id 123 \
  --bg_volume 0.2 --fx_volume 0.4 --target_lufs -16.0 --trailing_silence 0.5
```

### What it calls:
- **Service function**: `services.combine_export_audio.export_final_audio(text_id, options)`

### What the service does:
1. **Validation**: Checks prerequisites for audio combining:
   - Verifies text exists in database
   - Confirms segments exist with audio data (requires speech generation to be run first)
   - Reports availability of background music and sound effects

2. **Final Audio Export**: Creates professional-quality final audio:
   - Combines all speech segments in correct sequence order
   - Runs force alignment to generate word-level timestamps
   - Stores word timestamps in database for sound effect positioning
   - Normalizes speech to target LUFS (-18.0 for audiobooks)
   - Adds background music with 3-second intro and fade-out (if available)
   - Positions sound effects using word-level timestamps (if available)
   - Mixes all audio layers with configurable volumes
   - Adds optional trailing silence between segments

### Options:
- `--text_id`: ID of text to process (required)
- `--output_dir`: Directory to save output files (defaults to 'output')
- `--trailing_silence`: Silence between segments in seconds (default: 0.0)
- `--bg_volume`: Background music volume 0.0-1.0 (default: 0.15 = 15%)
- `--fx_volume`: Sound effects volume 0.0-1.0 (default: 0.3 = 30%)
- `--target_lufs`: Target loudness in LUFS (default: -18.0 for audiobooks)

### Requirements:
- Database connection configured
- Speech segments must exist with audio data (run speech generation first)
- FFmpeg installed for audio processing
- faster-whisper library for force alignment (optional but recommended)

### Output:
The script provides detailed logging and creates:
- Final mixed audio file with all available components
- Word-level timestamps stored in database (for sound effect positioning)
- Processing summary with file path, included components, and audio settings

### Audio Components:
The final audio will always include speech segments and may include:
- **Background music**: If available in database (at specified volume with fade effects)
- **Sound effects**: If available with audio data (positioned using word timestamps)
- **Professional mixing**: Normalized to target LUFS with proper volume balance

## CLI Wrapper Benefits

These CLI wrappers provide several advantages:

1. **Single Source of Truth**: All service logic exists only in `services/` - no duplication
2. **Maintainability**: Updates to service logic automatically benefit CLI wrappers
3. **Testability**: Services can be tested independently of CLI interface
4. **Consistency**: Same logic used by API endpoints and CLI wrappers
5. **Simplicity**: Thin wrappers focus only on argument parsing and service calls

**Architecture Pattern:**
```
CLI Wrapper (30 lines) → Service Function → Database Operation
```

Rather than duplicating service logic (150+ lines per script), these wrappers simply parse arguments and call the appropriate service function. 