# Indie Services - Standalone Scripts

This folder contains standalone versions of the services that can be run independently with database inputs.

## Text Analysis

**Script:** `text_analysis_standalone.py`

Analyzes text content and stores character and segment data in the database.

### Usage:

```bash
# Analyze existing text by ID
python3 scripts/indie-services/text_analysis_standalone.py --text-id 123

# Analyze text from file and create new database record
python3 scripts/indie-services/text_analysis_standalone.py --file scripts/input_interactive_e2e.txt --create-text

# Use default file (scripts/input_interactive_e2e.txt) and create new record
python3 scripts/indie-services/text_analysis_standalone.py --create-text
```

### What it does:
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

**Script:** `sound_effects.py`

Generates audio for existing sound effect records using Replicate webhooks.

### Usage:

```bash
# Generate audio for existing sound effects 
python3 scripts/indie-services/sound_effects.py --text-id 123

# Use parallel processing for faster generation
python3 scripts/indie-services/sound_effects.py --text-id 123 --parallel

# Automatically start FastAPI server if not running
python3 scripts/indie-services/sound_effects.py --text-id 123 --auto-start-server

# Skip server health check (advanced users)
python3 scripts/indie-services/sound_effects.py --text-id 123 --skip-server-check
```

### What it does:
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

### `background_music_standalone.py`

Generates background music for a specific text using Replicate's API via webhook.

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

## Other Services

Additional standalone services will be added here as they are developed. 