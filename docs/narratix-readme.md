# Narratix 2.0

## Overview
Narratix is an AI-powered platform that transforms text-based content into immersive graphic audio experiences. The platform targets publishers and content creators who want to convert their written works into engaging audio formats with distinct character voices.

This repository contains the rewritten, streamlined version of Narratix with cleaner architecture and improved workflows.

## Core Technologies
- **Backend**: Python with FastAPI
- **Database**: SQLite local db
- **AI Services**: 
  - Anthropic Claude API for text analysis
  - Hume AI for voice generation
- **Testing**: Pytest (minimal, focused on critical paths)
- **Logging**: Custom logging for API interactions

## System Architecture

### Data Model
```
Text
  ├── id: UUID
  ├── content: Text
  ├── title: String
  ├── created_at: Timestamp
  └── analyzed: Boolean

Character
  ├── id: UUID
  ├── text_id: UUID (Foreign Key to Text)
  ├── name: String
  ├── description: String
  ├── provider_id: String (Hume AI voice ID)
  └── created_at: Timestamp

TextSegment
  ├── id: UUID
  ├── text_id: UUID (Foreign Key to Text)
  ├── character_id: UUID (Foreign Key to Character)
  ├── content: Text
  ├── sequence: Integer
  ├── audio_file: String (path)
  └── created_at: Timestamp

ProcessLog
  ├── id: UUID
  ├── text_id: UUID (Foreign Key to Text)
  ├── timestamp: Timestamp
  ├── operation: String
  ├── request: JSON
  ├── response: JSON
  └── status: String
```

### Core Modules

#### 1. `db/`
- `models.py` - SQLAlchemy models for Text, Character, TextSegment, and ProcessLog
- `database.py` - Database connection and session management
- `crud.py` - CRUD operations for all models

#### 2. `services/`
- `text_analysis.py` - Anthropic Claude integration for text analysis
- `voice_generation.py` - Hume AI integration for voice creation
- `speech_generation.py` - Hume AI integration for TTS and audio processing

#### 3. `api/`
- `main.py` - FastAPI application entry point
- `endpoints/` - API route definitions
  - `text.py` - Text upload and management
  - `character.py` - Character management
  - `audio.py` - Audio generation and retrieval

#### 4. `utils/`
- `logging.py` - Custom logging utilities
- `config.py` - Configuration management

## Workflow

### 1. Text Processing
1. User submits text content
2. System checks if the text has been previously analyzed
   - If exists and analyzed, offer to re-analyze or proceed with existing analysis
   - If exists but not analyzed or does not exist, proceed to analysis

### 2. Text Analysis
1. Save text to database
2. Use Anthropic Claude to:
   - Identify characters in the text
   - Create character descriptions
   - Segment the text by speaking character
3. Save characters and text segments to database

### 3. Voice Generation
1. For each character without a provider_id:
   - Generate a unique voice using Hume AI
   - Save provider_id to character record

### 4. Audio Generation
1. For each text segment:
   - Generate audio using Hume AI TTS with the character's voice
   - Save audio file path to segment record
2. Combine segments if needed

### 5. Output
1. Provide complete audio file to user
2. Log entire process

## API Endpoints

### Text Management
- `POST /api/text` - Upload new text
- `GET /api/text/{text_id}` - Get text details
- `GET /api/text` - List all texts
- `PUT /api/text/{text_id}/analyze` - Trigger (re)analysis

### Character Management
- `GET /api/text/{text_id}/characters` - Get characters for text
- `PUT /api/character/{character_id}` - Update character details

### Audio Management
- `POST /api/text/{text_id}/generate-audio` - Generate audio for text
- `GET /api/text/{text_id}/audio` - Get generated audio

## Environment Setup

### Required Environment Variables
```
DATABASE_URL=sqlite:///./db/narratix.db
ANTHROPIC_API_KEY=your_anthropic_api_key
HUME_API_KEY=your_hume_api_key
```

### Development Setup
1. Create a virtual environment (`python -m venv venv` or `conda create -n narratix python=3.10`)
2. Activate the environment (`source venv/bin/activate` or `conda activate narratix`)
3. Install dependencies: `pip install -r requirements.txt`
4. The SQLite database (`narratix.db`) will be created automatically in the `db/` directory on first run.
5. Run database migrations: `alembic upgrade head`
6. Start the API: `uvicorn api.main:app --reload`

## Implementation Guidelines

### MVP Focus
- Begin with single-page story support
- Implement core functionality first:
  1. Text analysis
  2. Character voice generation
  3. Basic audio synthesis
- Minimize UI work initially, focus on API functionality

### Key Considerations
1. **Error Handling**: Robust error handling for AI services
2. **Logging**: Comprehensive logging of all AI interactions
3. **Idempotency**: Safe retry mechanisms for all operations
4. **Performance**: Efficient text segmentation and audio processing
5. **Cost Management**: Careful management of API calls to external services

## Future Enhancements
- Support for longer texts (chapters, books)
- Background music and sound effects
- User voice preferences and customization
- Multi-language support
- Batch processing for publishers
