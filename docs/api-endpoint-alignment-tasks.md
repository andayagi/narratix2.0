# API Endpoint-Service Alignment Tasks

## Overview
This document outlines the tasks required to fix the structural misalignment between services and API endpoints in the Narratix2.0 project.

## Current Problems

### 1. Services Without Dedicated Endpoints
- ~~`audio_analysis.py`~~ - **✅ COMPLETED** (unified soundscape + sound effects analysis)
- ~~`background_music.py`~~ - **✅ COMPLETED** (dedicated endpoint with full functionality)
- `combine_export_audio.py` - **NO DEDICATED ENDPOINT** (embedded in `/api/audio/`)
- `text_analysis.py` - **NO DEDICATED ENDPOINT** (embedded in `/api/text/`)

### 2. Inconsistent API Design
- Some services get dedicated endpoints (`sound_effects.py`, `voice_generation.py`)
- Others are buried inside multi-purpose endpoints
- Poor API discoverability and inconsistent usage patterns

### 3. Service Import Issues
- ✅ **FIXED**: Added missing imports to `services/__init__.py`

## Consistency Guidelines

Before implementing the tasks, all new endpoints must follow these consistency patterns:

### Naming Conventions
- **Endpoint URLs**: Use kebab-case (`/api/background-music/`, not `/api/background_music/`)
- **Route prefixes**: Always start with `/api/` followed by service name
- **Path parameters**: Use `{text_id}` format for consistency
- **Query parameters**: Use snake_case (`force_regenerate`, not `forceRegenerate`)

### HTTP Methods & Patterns
- **GET** - Retrieve data (no side effects)
  - `GET /{resource_id}` - Get single resource
  - `GET /{resource_id}/status` - Get resource status
  - `GET /{resource_id}/download` - Download files
- **POST** - Create or trigger operations
  - `POST /{resource_id}/process` - Run complete workflow
  - `POST /{resource_id}/analyze` - Run analysis
  - `POST /{resource_id}/generate` - Generate content
- **PUT** - Update existing resources
- **DELETE** - Remove resources

### Response Format Standards
All endpoints must return consistent JSON structure:

```python
# Success Response
{
    "text_id": int,
    "status": "success" | "processing" | "error" | "completed",
    "message": str,  # Optional descriptive message
    "data": {}       # Actual response data
}

# Error Response  
{
    "text_id": int,
    "status": "error",
    "message": str,
    "error_code": str,  # Optional error code
    "details": {}       # Optional error details
}
```

### Status Code Usage
- **200** - Success with data
- **201** - Created resource
- **202** - Accepted (for background tasks)
- **400** - Bad request (validation errors)
- **404** - Resource not found
- **500** - Internal server error

### Background Task Patterns
For long-running operations:
```python
@router.post("/{text_id}/process", status_code=202)
async def process_resource(text_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(service_function, db, text_id)
    return {
        "text_id": text_id,
        "status": "processing", 
        "message": "Task initiated in background"
    }
```

### Error Handling Patterns
```python
# Text not found
if not db_text:
    raise HTTPException(
        status_code=404, 
        detail=f"Text with ID {text_id} not found"
    )

# Prerequisites not met
if not db_text.analyzed:
    raise HTTPException(
        status_code=400,
        detail="Text must be analyzed before this operation"
    )

# Service errors
try:
    result = service.process(db, text_id)
except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=f"Operation failed: {str(e)}"
    )
```

### Parameter Validation
```python
# Required path parameters
text_id: int = Path(..., description="ID of the text to process")

# Optional query parameters with defaults
force: bool = Query(False, description="Force reprocessing if already exists")
format: str = Query("json", description="Response format")
```

### File Download Patterns
```python
@router.get("/{text_id}/download/{filename}")
async def download_file(text_id: int, filename: str):
    # Validate file exists and belongs to text
    file_path = validate_and_get_file_path(text_id, filename)
    
    with open(file_path, "rb") as f:
        content = f.read()
    
    return Response(
        content=content,
        media_type="audio/mpeg",  # or appropriate type
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

### Logging Standards
```python
# Operation start
logger.info(f"Starting {operation_name} for text ID {text_id}")

# Operation success
logger.info(f"Successfully completed {operation_name} for text ID {text_id}")

# Operation error
logger.error(f"Error in {operation_name} for text ID {text_id}: {str(e)}")
```

### Documentation Standards
Each endpoint must include:
```python
@router.post("/{text_id}/process")
async def process_resource(
    text_id: int,
    db: Session = Depends(get_db)
):
    """
    Process resource for a given text.
    
    Args:
        text_id: ID of the text to process
        
    Returns:
        Processing status and details
        
    Raises:
        404: Text not found
        400: Prerequisites not met
        500: Processing error
    """
```

## Tasks to Fix

### Task 1: Create Audio Analysis Endpoint ✅ **COMPLETED**
**Priority: HIGH** - This service has no API access point

#### Subtasks:
- [x] Create `api/endpoints/audio_analysis.py`
- [x] Implement endpoints:
  - `POST /api/audio-analysis/{text_id}/analyze` - Run unified analysis
  - `GET /api/audio-analysis/{text_id}` - Get analysis results
  - `GET /api/audio-analysis/{text_id}/soundscape` - Get soundscape only
  - `GET /api/audio-analysis/{text_id}/sound-effects` - Get sound effects only

#### Expected Functions:
```python
@router.post("/{text_id}/analyze")
async def analyze_audio_for_text(text_id: int, db: Session = Depends(get_db))

@router.get("/{text_id}")
async def get_audio_analysis(text_id: int, db: Session = Depends(get_db))

@router.get("/{text_id}/soundscape")
async def get_soundscape(text_id: int, db: Session = Depends(get_db))

@router.get("/{text_id}/sound-effects")
async def get_sound_effects_from_analysis(text_id: int, db: Session = Depends(get_db))
```

### Task 2: Create Background Music Endpoint ✅ **COMPLETED**
**Priority: MEDIUM** - Currently embedded in `/api/audio/`

#### Subtasks:
- [x] Create `api/endpoints/background_music.py`
- [x] Implement endpoints:
  - `POST /api/background-music/{text_id}/generate-prompt` - Generate music prompt
  - `POST /api/background-music/{text_id}/generate-audio` - Generate music audio
  - `POST /api/background-music/{text_id}/process` - End-to-end processing
  - `GET /api/background-music/{text_id}` - Get music status
  - `GET /api/background-music/{text_id}/audio` - Download music file

#### Expected Functions:
```python
@router.post("/{text_id}/generate-prompt")
async def generate_music_prompt(text_id: int, db: Session = Depends(get_db))

@router.post("/{text_id}/generate-audio")
async def generate_music_audio(text_id: int, db: Session = Depends(get_db))

@router.post("/{text_id}/process")
async def process_background_music(text_id: int, db: Session = Depends(get_db))

@router.get("/{text_id}")
async def get_background_music_status(text_id: int, db: Session = Depends(get_db))

@router.get("/{text_id}/audio")
async def download_background_music(text_id: int, db: Session = Depends(get_db))
```

### Task 3: Create Export Audio Endpoint ✅ **COMPLETED**
**Priority: MEDIUM** - Currently embedded in `/api/audio/`

#### Subtasks:
- [x] Create `api/endpoints/export_audio.py`
- [x] Implement endpoints:
  - `POST /api/export/{text_id}/combine-speech` - Combine speech segments
  - `POST /api/export/{text_id}/force-align` - Run force alignment
  - `POST /api/export/{text_id}/final-audio` - Export final mixed audio
  - `GET /api/export/{text_id}/status` - Get export status
  - `GET /api/export/{text_id}/download/{filename}` - Download exported files

#### Expected Functions:
```python
@router.post("/{text_id}/combine-speech")
async def combine_speech_segments_endpoint(text_id: int, db: Session = Depends(get_db))

@router.post("/{text_id}/force-align")
async def run_force_alignment(text_id: int, db: Session = Depends(get_db))

@router.post("/{text_id}/final-audio")
async def export_final_audio_endpoint(text_id: int, db: Session = Depends(get_db))

@router.get("/{text_id}/status")
async def get_export_status(text_id: int, db: Session = Depends(get_db))

@router.get("/{text_id}/download/{filename}")
async def download_exported_file(text_id: int, filename: str)
```

### Task 4: Create Text Analysis Endpoint ✅ **COMPLETED**
**Priority: LOW** - Currently accessible via `/api/text/{id}/analyze`

#### Subtasks:
- [x] Create `api/endpoints/text_analysis.py`
- [x] Implement endpoints:
  - `POST /api/text-analysis/{text_id}/analyze` - Run full analysis
  - `POST /api/text-analysis/{text_id}/characters` - Extract characters only
  - `POST /api/text-analysis/{text_id}/segments` - Extract segments only
  - `GET /api/text-analysis/{text_id}` - Get analysis results
  - `GET /api/text-analysis/{text_id}/characters` - Get characters
  - `GET /api/text-analysis/{text_id}/segments` - Get segments

#### Expected Functions:
```python
@router.post("/{text_id}/analyze")
async def analyze_text_full(text_id: int, force: bool = False, db: Session = Depends(get_db))

@router.post("/{text_id}/characters")
async def extract_characters(text_id: int, db: Session = Depends(get_db))

@router.post("/{text_id}/segments")
async def extract_segments(text_id: int, db: Session = Depends(get_db))

@router.get("/{text_id}")
async def get_text_analysis_results(text_id: int, db: Session = Depends(get_db))

@router.get("/{text_id}/characters")
async def get_characters(text_id: int, db: Session = Depends(get_db))

@router.get("/{text_id}/segments")
async def get_segments(text_id: int, db: Session = Depends(get_db))
```

### Task 5: Update Main API Router ✅ **COMPLETED**
**Priority: HIGH** - Required for all new endpoints

#### Subtasks:
- [x] Update `api/main.py` to include audio_analysis router
- [x] Update `api/main.py` to include background_music router
- [x] Update `api/main.py` to include export_audio router
- [x] Update `api/main.py` to include text_analysis router

### Task 6: Refactor Existing Endpoints ✅ **COMPLETED**
**Priority: LOW** - Clean up after new endpoints are created

#### Subtasks:
- [x] Remove embedded functionality from `/api/audio/` that's now in dedicated endpoints
- [x] Remove embedded functionality from `/api/text/` that's now in dedicated endpoints  
- [x] Update any existing API calls to use new dedicated endpoints
- [x] Add deprecation warnings for old embedded endpoints

#### What was completed:

**1. Added Deprecation Warnings to Old Endpoints:**
- `POST /api/audio/text/{text_id}/background-music` → deprecated, use `/api/background-music/{text_id}/process`
- `GET /api/audio/text/{text_id}/background-music` → deprecated, use `/api/background-music/{text_id}`
- `POST /api/audio/text/{text_id}/export` → deprecated, use `/api/export/{text_id}/final-audio`
- `POST /api/audio/text/{text_id}/force-align` → deprecated, use `/api/export/{text_id}/force-align`
- `PUT /api/text/{text_id}/analyze` → deprecated, use `/api/text-analysis/{text_id}/analyze`

**2. Updated Internal API Calls:**
- `flow.md` - Updated workflow documentation to reference new endpoints
- `scripts/interactive_e2e_processing.py` - Updated to use new text-analysis endpoint
- `tests/test_end_to_end.py` - Updated to use new text-analysis endpoint
- `docs/narratix-readme.md` - Added documentation for new dedicated endpoints

**3. Backward Compatibility:**
- All deprecated endpoints still work but show deprecation warnings
- Response objects include warning messages pointing to new endpoints
- No breaking changes - clients can migrate gradually

**4. Consistent Warning Format:**
- All deprecated endpoints include Python `warnings.warn()` for development
- All response objects include `"warning"` field with migration guidance
- Clear documentation markers (⚠️ DEPRECATED) in docstrings

#### Notes:
- Maintained full backward compatibility during transition
- All new dedicated endpoints follow consistent design patterns
- Migration path is clear and documented
- Old endpoints can be removed in future major version update

## Final API Structure

After completion, the API will have consistent structure:

```bash
# Service-to-Endpoint Mapping
/api/text/              ←→ text.py (CRUD operations)
/api/text-analysis/     ←→ text_analysis.py (analysis operations)
/api/character/         ←→ voice_generation.py (character voice operations)
/api/audio/             ←→ speech_generation.py (speech generation)
/api/audio-analysis/    ←→ audio_analysis.py (unified audio analysis)
/api/background-music/  ←→ background_music.py (music operations)
/api/sound-effects/     ←→ sound_effects.py (sound effects operations)
/api/export/            ←→ combine_export_audio.py (export operations)
```

## Implementation Order

1. ~~**Task 1** (Audio Analysis)~~ - ✅ **COMPLETED**
2. ~~**Task 2** (Background Music)~~ - ✅ **COMPLETED**
3. ~~**Task 3** (Export Audio)~~ - ✅ **COMPLETED**
4. ~~**Task 4** (Text Analysis)~~ - ✅ **COMPLETED**
5. ~~**Task 5** (Update Main Router)~~ - ✅ **COMPLETED** (all endpoints added)
6. **Task 6** (Refactor Existing) - Cleanup

## Success Criteria

- [x] Audio Analysis service has dedicated, discoverable endpoints
- [x] Background Music service has dedicated, discoverable endpoints
- [x] Export Audio service has dedicated, discoverable endpoints
- [x] Text Analysis service has dedicated, discoverable endpoints
- [x] Consistent API design patterns across all endpoints (all new endpoints follow guidelines)
- [x] No functionality is lost during refactoring (all new endpoints maintain full service functionality)
- [ ] All new endpoints are properly tested
- [ ] API documentation is updated to reflect new structure

## Notes

- Maintain backward compatibility during transition
- Consider adding API versioning if breaking changes are needed
- Update client applications to use new dedicated endpoints
- Monitor for any performance impact from the restructuring 