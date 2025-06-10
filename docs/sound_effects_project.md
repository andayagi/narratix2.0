# Sound Effects Implementation Plan - Midsummerr

## Overview
Adding cinematic sound effects layer to existing Midsummerr audio production pipeline to achieve graphic audio quality. Sound effects are implemented as a **separate processing step** that analyzes the complete text independently from existing text analysis.

**Key Principle**: Sound effects are completely separate from text analysis. They analyze the entire text content as an independent processing step.

## Current Production Flow
1. Text analysis → Character identification + segmentation
2. Voice generation (Hume AI) → Individual character voices  
3. Speech generation → TTS for all segments
4. Background music generation (Replicate) → Genre-appropriate music
5. Audio mixing → Combined final output

## Proposed Enhanced Flow

### Phase 1: Database Schema Setup
**Create dedicated sound effects table and database operations**

**New Sound Effects Table:**
```sql
CREATE TABLE sound_effects (
    effect_id INTEGER PRIMARY KEY AUTOINCREMENT,
    effect_name VARCHAR NOT NULL,           -- e.g., "wooden-door-creak"
    text_id INTEGER NOT NULL,               -- FK to texts table
    segment_id INTEGER,                     -- Optional FK to text_segments table (can be NULL)
    start_word VARCHAR NOT NULL,            -- Word where effect starts
    end_word VARCHAR NOT NULL,              -- Word where effect ends
    start_word_position INTEGER,            -- Position/index of start word in text (1-based)
    end_word_position INTEGER,              -- Position/index of end word in text (1-based)
    prompt TEXT NOT NULL,                   -- AudioX generation prompt
    audio_data_b64 TEXT NOT NULL,           -- Base64 encoded audio
    start_time FLOAT,                       -- Actual start time in seconds (from alignment)
    end_time FLOAT,                         -- Actual end time in seconds (from alignment)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (text_id) REFERENCES texts (id),
    FOREIGN KEY (segment_id) REFERENCES text_segments (id)  -- Optional relationship
);

-- Add indexes for performance
CREATE INDEX idx_sound_effects_text_id ON sound_effects(text_id);
CREATE INDEX idx_sound_effects_timing ON sound_effects(start_time, end_time);
```

### Phase 2: Speech & Alignment Pipeline
**Decoupled and timestamp-based workflow**
- **Invalidation First**: Before generating new speech segments, any existing force alignment data for the text is **invalidated** (cleared from the database). This ensures that any change to the speech requires a fresh alignment.
- **Speech Generation**: Generate TTS for all segments (existing logic).
- **Combine Speech-Only Audio**: After speech is generated, all segments are combined into a single, unified **speech-only** audio file. This file is temporary and used exclusively for alignment.
- **Force Alignment**: Run WhisperX on the speech-only audio file to generate precise, word-level timestamps.
- **Store Timestamps**: The complete list of word timestamps is stored as JSON in the `texts.word_timestamps` column, and the generation time is saved in `texts.force_alignment_timestamp`.

**Word-Level Timing Output:**
```python
# Example WhisperX output (from speech-only audio)
[
  {"word": "door", "start": 2.1, "end": 2.6},
  {"word": "creaked", "start": 2.7, "end": 3.2}
]
```

**Storage & Validation:** Complete word timestamps are stored in the database. The `force_alignment_timestamp` is used to validate if the alignment is newer than any segment's `last_updated` time, ensuring data consistency.

### Phase 3: Independent Sound Effect Analysis & Generation
**New service: `services/sound_effects.py`**
- **Completely separate from existing text analysis**
- Analyzes entire text content independently using Claude
- **Uses stable, speech-only word timestamps from Phase 2 for precise timing**
- Generate custom sound effects via AudioX with precise durations

**Complete Text Analysis for Sound Effects:**
```python
def analyze_text_for_sound_effects(text_content: str, word_timestamps: List[Dict]) -> List[Dict]:
    """
    Analyzes the complete text using Claude to identify sound opportunities
    Uses word timestamps for precise timing decisions
    
    Returns list of sound effect specifications with word positions:
    [
        {
            "effect_name": "thunder-distant",
            "start_word": "thunder", 
            "end_word": "thunder",
            "start_word_position": 3,  # First occurrence of "thunder"
            "end_word_position": 3,
            "prompt": "distant thunder rumbling softly",
            "duration": 1.2  # Calculated from word timestamps
        }
    ]
    """
```

**Smart Timing-Based Generation:**
```python
# Generate door creak with exact duration needed
result = client.predict(
    prompt="old wooden door creaking open slowly, horror movie style",
    seconds_total=calculate_effect_duration(word_timestamps, "door", "creaked"),  # e.g., 1.1s
    cfg_scale=8,
    api_name="/generate_cond"
)
```

**Word Position Tracking**: 
- For texts with repeated words (e.g., "thunder appears twice"), word positions distinguish which occurrence:
  - "Suddenly a thunder far away" - first "thunder" = position 3
  - "then another loud thunder" - second "thunder" = position 13
- This prevents ambiguity when the same word appears multiple times

### Phase 4: Advanced Audio Mixing
**Enhanced `services/combine_export_audio.py`**
- Layer sound effects at precise timestamps using ffmpeg
- Maintain existing voice + background music mixing
- Handle volume balancing between all audio layers

## Technical Implementation

### Dependencies & Environment Setup
**New Python Dependencies (add to requirements.txt):**
```txt
whisperx>=3.1.1              # Force alignment for word-level timing
torch>=2.0.0                 # Required by WhisperX
torchaudio>=2.0.0            # Audio processing for WhisperX
faster-whisper>=0.9.0        # Faster inference backend
```

**System Requirements:**
- GPU support recommended for WhisperX (CUDA/Metal)
- Minimum 8GB RAM for local WhisperX processing
- ffmpeg with additional codecs for advanced mixing

**Environment Variables (add to .env):**
```env
# Sound Effects Configuration
WHISPERX_MODEL_SIZE=base          # Options: tiny, base, small, medium, large
WHISPERX_COMPUTE_TYPE=float16     # Performance optimization
SOUND_EFFECTS_VOLUME_LEVEL=0.3    # Default volume for effects (0.0-1.0)
```

### Database Changes
**Add to `db/models.py`:**
```python
class SoundEffect(Base):
    __tablename__ = "sound_effects"
    
    effect_id = Column(Integer, primary_key=True, autoincrement=True)
    effect_name = Column(String, nullable=False)
    text_id = Column(Integer, ForeignKey("texts.id"), nullable=False)
    segment_id = Column(Integer, ForeignKey("text_segments.id"), nullable=True)  # Optional
    start_word = Column(String, nullable=False)
    end_word = Column(String, nullable=False)
    start_word_position = Column(Integer, nullable=True)  # Position of start word in text
    end_word_position = Column(Integer, nullable=True)    # Position of end word in text
    prompt = Column(Text, nullable=False)
    audio_data_b64 = Column(Text, nullable=False)
    start_time = Column(Float, nullable=True)  # From force alignment
    end_time = Column(Float, nullable=True)    # From force alignment
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    text = relationship("Text", back_populates="sound_effects")
    segment = relationship("TextSegment", back_populates="sound_effects")

# Update existing models with relationships
class Text(Base):
    # ... existing code ...
    sound_effects = relationship("SoundEffect", back_populates="text")
    word_timestamps = Column(JSON, nullable=True)  # Store complete word-level timing data
    force_alignment_timestamp = Column(DateTime(timezone=True), nullable=True) # When alignment was created

class TextSegment(Base):
    # ... existing code ...
    sound_effects = relationship("SoundEffect", back_populates="segment")
```

### API Endpoints
**New endpoints in `main.py` or dedicated router:**
```python
@app.post("/api/audio/{text_id}/force-align")
async def run_force_alignment(text_id: int):
    """Run force alignment on the speech-only audio for a text"""

@app.post("/api/sound-effects/analyze/{text_id}")
async def analyze_sound_effects(text_id: int):
    """Analyze text for sound effect opportunities"""

@app.post("/api/sound-effects/generate/{text_id}")
async def generate_sound_effects(text_id: int):
    """Generate sound effects for analyzed opportunities"""

@app.get("/api/sound-effects/{text_id}")
async def get_sound_effects(text_id: int):
    """Get all sound effects for a text"""

@app.delete("/api/sound-effects/{effect_id}")
async def delete_sound_effect(effect_id: int):
    """Remove a specific sound effect"""
```

### Error Handling & Recovery
**Critical Error Scenarios:**
1. **WhisperX Alignment Failure**: Fallback to basic word timing estimation
2. **AudioX Generation Timeout**: Retry with simpler prompts
3. **Memory Issues**: Process large texts in chunks, cleanup resources
4. **Audio Corruption**: Validate generated audio before storage

**Retry Logic:**
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def generate_sound_effect_with_retry(prompt: str, duration: float):
    """AudioX generation with exponential backoff retry"""
```

### Performance Considerations
**Resource Management:**
- WhisperX model loading optimization to avoid reloading
- Batch processing for multiple sound effects
- Database connection pooling for high-frequency operations
- Background task queue for non-blocking generation

**Storage Optimization:**
- Compress audio data before base64 encoding
- Consider cloud storage for large audio files

### Core Tools & Libraries

#### Free/Open Source Tools
- **WhisperX** - Force alignment for word-level timing (free, local)
- **AudioX API** - AI sound effect generation (existing integration)
- **ffmpeg** - Audio processing and mixing (existing)
- **Claude/Anthropic** - Independent text analysis for sound effects (existing)

#### Architecture
- **FastAPI Backend** - Existing Python service architecture
- **Local Processing** - WhisperX runs on same server (no API costs)
- **Database** - SQLite with dedicated sound_effects table
- **File Storage** - Generated effects stored locally/cloud

### Testing Strategy
**MVP Testing (minimal viable validation):**
- Basic end-to-end test: text → sound effects → final audio
- Manual validation of sound quality with sample text
- Database operations work without errors

**Skip for MVP:**
- Unit tests, performance tests, comprehensive error scenarios
- Detailed validation - focus on shipping working features

### Implementation Phases

#### Week 1: Database Schema Setup - DONE
1. [x] Create migration files for the new table
2. [x] Add `SoundEffect` model to `db/models.py`
3. [x] Add CRUD operations to `db/crud.py`
4. [x] Run migrations: `alembic upgrade head`

#### Week 2: Speech & Alignment Pipeline Refactor - DONE
1. [x] Update `texts` table schema to include `word_timestamps` (JSON) and `force_alignment_timestamp` (DateTime).
2. [x] Create a dedicated `force_alignment.py` service to run alignment on speech-only audio.
3. [x] Implement logic in `speech_generation.py` to invalidate (clear) old alignment data before generating new speech.
4. [x] Add API endpoint to manually trigger force alignment.

#### Week 3: Independent Sound Effect Analysis & Generation - IN PROGRESS
1. [x] Create `sound_effects.py` service with complete text analysis
2. [x] Implement word position calculation and tracking
3. [x] Integrate AudioX for effect generation with timing-aware prompts (placeholder implemented)
4. [ ] Test sound quality and precise duration matching

#### Week 4: Advanced Audio Mixing
1. Extend `combine_export_audio.py` for multi-layer mixing
2. Layer effects at exact timestamps from force alignment, BEFORE adding the background music
3. Volume balancing and quality optimization
4. End-to-end testing with complete pipeline

### Rollback Plan
**If Issues Arise:**
1. Feature flag to disable sound effects pipeline
2. Database migration rollback scripts
3. Audio generation bypass for critical production
4. Monitoring alerts for generation failures

