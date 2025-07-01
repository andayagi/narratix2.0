# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Coding guidelines: 
1. Code the MINIMUM to get the job done
2. in terminal, explain shortly each action you take. be very consice. 
3. ALWAYS solve bugs and errors at their root cause, workarounds and fallbacks should be approved before coding them
4. When editing an existing service\utils\endpoints (and such) always check files it effects and edit them if needed. 
5. When asked to perfrom a task from a tasks file, always update it once you're done.
6. When tackling a new task or planning something, you should take into account the project's architecture.

## Project Overview

Narratix 2.0 is an AI-powered platform that transforms text into immersive graphic audio experiences. It's a Python FastAPI application that uses external AI services (Anthropic Claude, Hume AI, Replicate) to analyze text, generate character voices, create speech, add background music, and incorporate sound effects.


## Development Commands

### Database Operations
```bash
# Run database migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

### Running the Application
```bash
# Start the development server
uvicorn api.main:app --reload

# Run with specific port
uvicorn api.main:app --reload --port 8000
```

### Testing
```bash
# Run all tests
pytest

# Run integration tests only
pytest -m integration

# Run specific test file with verbose output
pytest -xvs tests/test_voice_generation_integration.py

# Run integration tests with script
./tests/run_integration_tests.sh
```

### Standalone Services
The `scripts/indie-services/` directory contains standalone scripts that can run independently:
- `text_analysis_standalone.py` - Text analysis without API
- `voice_generation.py` - Voice generation standalone
- `speech_generation.py` - Speech generation standalone
- `background_music_standalone.py` - Background music generation
- `sound_effects_standalone.py` - Sound effects generation
- `combine_export_audio_standalone.py` - Audio combination and export
- `audio_analysis_standalone.py` - Audio analysis standalone

### Pipeline Scripts
```bash
# Run simple end-to-end pipeline
python scripts/simple_e2e_pipeline.py

# Run interactive end-to-end processing
python scripts/interactive_e2e_processing.py

# Run speech pipeline
python scripts/track1_speech_pipeline.py

# Run audio pipeline
python scripts/track2_audio_pipeline.py
```

## Architecture Overview

### Core Services (`services/`)
- **text_analysis.py**: Uses Anthropic Claude to identify characters and segment text
- **voice_generation.py**: Creates character voices using Hume AI
- **speech_generation.py**: Generates speech audio using Hume AI TTS
- **background_music.py**: Generates background music using Replicate
- **sound_effects.py**: Creates sound effects using Replicate
- **combine_export_audio.py**: Combines all audio components using FFmpeg
- **audio_analysis.py**: Analyzes audio for timing and synchronization

### Database Models (`db/models.py`)
- **Text**: Main text content with analysis flags and metadata
- **Character**: Extracted characters with voice provider IDs and descriptions
- **TextSegment**: Text segments assigned to characters with audio data
- **SoundEffect**: Sound effects with timing and positioning data
- **ProcessLog**: Operation logging for debugging and monitoring

### API Structure (`api/endpoints/`)
- **text.py**: Text upload and management endpoints
- **character.py**: Character management and voice assignment
- **audio.py**: Audio generation and retrieval
- **text_analysis.py**: Text analysis triggers and results
- **background_music.py**: Background music generation
- **sound_effects.py**: Sound effects analysis and generation
- **export_audio.py**: Final audio export and force alignment
- **replicate_webhook.py**: Webhook handling for async operations

### External Integrations
- **Anthropic Claude**: Text analysis, character extraction, sound effects analysis
- **Hume AI**: Voice generation, speech synthesis
- **Replicate**: Background music generation, sound effects creation
- **FFmpeg**: Audio processing, combining, and format conversion
- **WhisperX**: Force alignment for word-level timestamps

## Configuration

### Required Environment Variables
```bash
DATABASE_URL=sqlite:///./db/narratix.db
ANTHROPIC_API_KEY=your_anthropic_api_key
HUME_API_KEY=your_hume_api_key
REPLICATE_API_TOKEN=your_replicate_token
```

### Optional Configuration
- `WEBHOOK_MONITORING_ENABLED`: Enable webhook failure monitoring
- `WEBHOOK_FAILURE_ALERT_THRESHOLD`: Failure count threshold for alerts
- `WEBHOOK_TIMEOUT_SECONDS`: Webhook timeout configuration
- `CORS_ORIGINS`: CORS configuration for production

## Development Workflow

### Processing Pipeline Structure

The pipeline operates on two independent tracks that run in parallel:

#### Track 1: Speech Pipeline
1. **Text Analysis**: PUT to `/api/text-analysis/{text_id}/analyze`
2. **Voice Generation** (parallel): PUT to `/api/character/{character_id}/voice` for each character
3. **Speech Generation** (parallel): POST to `/api/audio/text/{text_id}/generate` for each utterance

#### Track 2: Audio Pipeline
1. **Audio Analysis**: Analyze content for background music and sound effects requirements
2. **Background Music Generation** (parallel): POST to `/api/background-music/{text_id}/process`
3. **Sound Effects Generation** (parallel): POST to `/api/sound-effects/analyze/{text_id}`

#### Final Combination
- **Export**: POST to `/api/export/{text_id}/final-audio` (requires both tracks to complete)

### Pipeline Dependencies
- **Track 1**: Text Analysis → Voice Generation (parallel) → Speech Generation (parallel)
- **Track 2**: Audio Analysis → Background Music || Sound Effects (both parallel)
- Both tracks run independently and are combined at the end

### Key Data Flow
- Text → Characters → TextSegments → Audio Files → Combined Output
- Async operations use webhooks for completion notifications
- All operations are logged in ProcessLog for debugging
- Audio files stored as base64 in database with optional file paths

## Testing Strategy

Integration tests make real API calls and require valid API keys. Test data persists in database for inspection. The application uses SQLite for development with automatic table creation.

## File Organization

- `audio_files/`: Generated audio organized by date
- `output/`: Final combined audio outputs
- `logs/`: Session-based logging files
- `alembic/`: Database migration files
- `utils/`: Configuration, logging, and HTTP utilities
- `schemas/`: Pydantic schemas for API validation

## Important Considerations

- All external API calls are logged with request/response data
- Database uses integer IDs (not UUIDs as originally planned)
- Audio processing requires FFmpeg system dependency
- Force alignment requires WhisperX and PyTorch dependencies
- Webhook endpoints include failure monitoring and alerts
- CORS configuration is environment-aware (dev vs production)