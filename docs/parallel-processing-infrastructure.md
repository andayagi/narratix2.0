# PRD: Parallel Processing Infrastructure for Text-to-Audio Pipeline


## Executive Summary

This PRD outlines the requirements for implementing parallel processing in the Narratix text-to-audio pipeline to reduce total processing time by **~35%** (from 6m 11s to 4m 0s). The solution leverages existing async infrastructure with our new unified audio analysis service, targeting a **131-second reduction** through strategic parallelization and API optimization.

**Key Benefits:**
- ⚡ **131-second time savings** with unified audio analysis and parallel processing
- 🛠️ **45-minute implementation** using existing architecture plus new unified service
- 💰 **Reduced API costs** (50% fewer Anthropic calls for audio analysis)
- 🎯 **Improved user experience** with faster audio generation
- 🔧 **Simplified dependencies** (no force alignment required)

---

## Problem Statement

### Current Pain Points
1. **Sequential Processing Bottleneck**: Services run one-after-another despite being independent
2. **Duplicate Analysis Overhead**: Separate Anthropic calls for background music and sound effects
3. **Force Alignment Complexity**: Heavy dependency on audio segments for timing data
4. **User Wait Time**: 6+ minute processing creates poor UX for real-time applications  
5. **Resource Underutilization**: System idle during single-service execution

### Recent Optimizations Implemented
**Unified Audio Analysis Service**: 
- Combined background music and sound effects analysis into single Anthropic call
- Replaced force alignment with simple word placement (numerical positions)
- Reduced API complexity and improved reliability
- 50% reduction in Claude API calls for audio analysis

### Updated Analysis Results
Based on log analysis with unified audio analysis implementation:

| **Service** | **Original Duration** | **Optimized Duration** | **Parallelization Potential** |
|-------------|----------------------|------------------------|-------------------------------|
| Unified Audio Analysis | ~150s (combined) | ~80s (single call) | ✅ High (generates both outputs) |
| Background Music Generation | 77.45s | 77.45s | ✅ High (uses unified analysis output) |
| Sound Effects Generation | 131.60s | 131.60s | ✅ High (uses unified analysis output) |
| Voice Generation | 31.48s | 31.48s | ✅ Medium (character-based) |
| Text Analysis | 84.40s | 84.40s | ⚠️ Low (sequential dependencies) |
| Audio Assembly | 7.11s | 7.11s | ⚠️ Low (requires all inputs) |

**Net Improvement**: ~70s from unified analysis + ~61s from parallelization = **131s total savings**

---

### Primary Goals
Reduce total pipeline time

---

## Requirements

### Functional Requirements

#### FR1: Unified Audio Analysis
- **FR1.1**: Single Anthropic call generates both soundscape and sound effects analysis
- **FR1.2**: Use word placement for audio analysis instead of force alignment for positioning
- **FR1.3**: Maintain separation between background music generation and sound effects generation
- **FR1.4**: Ensure consistent analysis quality with previous separate calls

#### FR2: Parallel Service Execution
- **FR2.1**: Execute audio generation services simultaneously using `asyncio.gather()`
- **FR2.2**: Maintain sequential execution for dependent services
- **FR2.3**: Support parallel voice generation for multiple characters
- **FR2.4**: Enable concurrent background music and sound effects generation after unified analysis

#### FR3: Error Handling & Resilience
- **FR3.1**: Isolate service failures (one failure doesn't stop others - except speech processes!)
- **FR3.2**: Implement timeout handling for each parallel service
- **FR3.3**: Provide detailed logging for parallel execution status
- **FR3.4**: Support retry mechanism for failed services

#### FR4: Resource Management
- **FR4.1**: Scale database connection pool for concurrent operations
- **FR4.2**: Optimize HTTP client reuse across parallel services
- **FR4.3**: Monitor and limit resource consumption during parallel execution

### Non-Functional Requirements

#### NFR1: Performance
- **NFR1.1**: Achieve 30-35% reduction in total processing time
- **NFR1.2**: Maintain <100ms overhead for parallel coordination
- **NFR1.3**: Support up to 12 concurrent service operations
- **NFR1.4**: 50% reduction in Anthropic API calls for audio analysis

#### NFR2: Scalability
- **NFR2.1**: Handle increased database connections (5 → 25 pool size)
- **NFR2.2**: Support burst capacity (35 max overflow connections)
- **NFR2.3**: Graceful degradation under high load

#### NFR3: Reliability
- **NFR3.1**: Maintain 99.9% uptime during parallel operations
- **NFR3.2**: Zero data corruption or loss during concurrent processing
- **NFR3.3**: Consistent output quality regardless of execution mode
- **NFR3.4**: Simplified error handling

#### NFR4: Maintainability
- **NFR4.1**: Use existing async infrastructure
- **NFR4.2**: Preserve current service interfaces and contracts
- **NFR4.3**: Maintain backward compatibility with sequential execution
- **NFR4.4**: Simplified word placement approach for analysis reduces maintenance overhead

---

## Technical Specifications

### Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Layer                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─── PARALLEL TRACK 1: SPEECH GENERATION ─────────┐       │
│  │                                                  │       │
│  │  1.1 Text Analysis (Sequential)                 │       │
│  │  ┌─────────────────┐                            │       │
│  │  │ Text Analysis   │                            │       │
│  │  │ (84.4s)         │                            │       │
│  │  └─────────────────┘                            │       │
│  │             │                                   │       │
│  │             ▼                                   │       │
│  │  1.2 Voice Generation (Parallel)                │       │
│  │  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │       │
│  │  │ Voice Gen   │ │ Voice Gen   │ │ Voice Gen  │ │       │
│  │  │ Char 1      │ │ Char 2      │ │ Char 3     │ │       │
│  │  │ (3.9s)      │ │ (19.6s)     │ │ (8s)       │ │       │
│  │  └─────────────┘ └─────────────┘ └────────────┘ │       │
│  └──────────────────────────────────────────────────┘       │
│                                                             │
│                         ║                                   │
│                    RUNS IN PARALLEL                         │
│                         ║                                   │
│  ┌─── PARALLEL TRACK 2: SOUNDSCAPE GENERATION ─────┐       │
│  │                                                  │       │
│  │  2.1 Audio Analysis (Sequential)                 │       │
│  │  ┌─────────────────┐                            │       │
│  │  │ Unified Audio   │                            │       │
│  │  │ Analysis (80s)  │                            │       │
│  │  └─────────────────┘                            │       │
│  │             │                                   │       │
│  │             ▼                                   │       │
│  │  2.2 Audio Generation (Parallel)                │       │
│  │  ┌─────────────────┐  ┌─────────────────┐      │       │
│  │  │ Background      │  │ Sound Effects   │      │       │
│  │  │ Music Gen       │  │ Generation      │      │       │
│  │  │ (77.4s)         │  │ (131.6s)        │      │       │
│  │  └─────────────────┘  └─────────────────┘      │       │
│  └──────────────────────────────────────────────────┘       │
│                                                             │
│                         ║                                   │
│                   AFTER BOTH COMPLETE                       │
│                         ║                                   │
│                         ▼                                   │
│  3. Audio Assembly (Sequential - requires force alignment)  │
│  ┌─────────────────┐                                       │
│  │ Audio Assembly  │                                       │
│  │ + Force Align   │                                       │
│  │ (7.11s)         │                                       │
│  └─────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

### Unified Audio Analysis Implementation

**New Service Architecture:**
```python
# services/audio_analysis.py - Unified Analysis
@time_it("unified_audio_analysis")
async def analyze_text_for_audio(db: Session, text_id: int) -> Tuple[Optional[str], List[Dict]]:
    """
    Single Claude call that generates both soundscape and sound effects.
    Uses word placement instead of force alignment for positioning.
    """
    
    # Create word placement data (simple numerical positions)
    words = full_text.split()
    word_placement = [{"word": word, "placement": i} for i, word in enumerate(words, 1)]
    
    # Single Anthropic call for both analyses
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        messages=[{
            "role": "user", 
            "content": unified_analysis_prompt_with_word_placement
        }]
    )
    
    # Returns both soundscape and sound_effects from single response
    return soundscape, sound_effects
```

### Database Infrastructure Changes

**Updated Configuration:**
```python
# db/database.py - Enhanced for unified approach
engine = create_engine(
    DATABASE_URL,
    pool_size=25,           # Increased for parallel operations
    max_overflow=35,        # Higher burst capacity
    pool_pre_ping=True,     # Verify connection health
    pool_recycle=3600       # Refresh connections hourly
)
```

### Optimized Orchestrator Implementation

**Core Parallel Execution Logic:**
```python
# scripts/interactive_e2e_processing.py
import asyncio
from typing import List, Dict, Any
from services.audio_analysis import analyze_text_for_audio

async def run_optimized_parallel_pipeline(text_id: int) -> Dict[str, Any]:
    """Execute text-to-audio pipeline with two main parallel tracks."""
    
    async def speech_generation_track():
        """Track 1: Speech Generation - Text Analysis → Parallel Voice Generation"""
        # 1.1 Text Analysis (Sequential)
        text_analysis = await run_text_analysis_pipeline(text_id)
        
        # 1.2 Voice Generation (Parallel by character)
        characters = text_analysis.get('characters', [])
        voice_tasks = [
            generate_character_voice(db, text_id, char) 
            for char in characters
        ]
        voice_results = await asyncio.gather(*voice_tasks, return_exceptions=True)
        
        return {
            'text_analysis': text_analysis,
            'voices': voice_results
        }
    
    async def soundscape_generation_track():
        """Track 2: Soundscape Generation - Audio Analysis → Parallel BG/SFX Generation"""
        # 2.1 Audio Analysis (Sequential)
        soundscape, sound_effects = await analyze_text_for_audio(db, text_id)
        
        # 2.2 Audio Generation (Parallel - BG music and SFX)
        audio_generation_tasks = await asyncio.gather(
            generate_background_music_from_soundscape(db, text_id, soundscape),
            generate_sound_effects_from_analysis(db, text_id, sound_effects),
            return_exceptions=True  # Isolate failures
        )
        
        return {
            'unified_audio_analysis': {'soundscape': soundscape, 'sound_effects': sound_effects},
            'background_music': audio_generation_tasks[0],
            'sound_effects': audio_generation_tasks[1]
        }
    
    # Execute both tracks in parallel
    speech_results, soundscape_results = await asyncio.gather(
        speech_generation_track(),
        soundscape_generation_track(),
        return_exceptions=True
    )
    
    # 3. Audio Assembly (Sequential - requires force alignment and all inputs)
    final_audio = await assemble_final_audio_with_force_alignment(db, text_id)
    
    return {
        **speech_results,
        **soundscape_results,
        'final_audio': final_audio
    }
```

### Error Handling Strategy

**Enhanced Service Isolation:**
```python
async def execute_with_fallback(service_func, service_name: str, timeout: int = 300):
    """Execute service with timeout and error isolation."""
    try:
        result = await asyncio.wait_for(service_func(), timeout=timeout)
        logger.info(f"✅ {service_name} completed successfully")
        return result
    except asyncio.TimeoutError:
        logger.error(f"⏰ {service_name} timed out after {timeout}s")
        return None
    except Exception as e:
        logger.error(f"❌ {service_name} failed: {str(e)}")
        return None

async def execute_unified_analysis_with_fallback(db: Session, text_id: int):
    """Execute unified analysis with fallback to sequential calls if needed."""
    try:
        return await analyze_text_for_audio(db, text_id)
    except Exception as e:
        logger.warning(f"Unified analysis failed, falling back to sequential: {e}")
        # Fallback to separate calls if unified analysis fails
        soundscape = await generate_background_music_prompt(db, text_id)
        sound_effects = await analyze_text_for_sound_effects(db, text_id)
        return soundscape, sound_effects
```

---

## Implementation Plan

### Phase 1: Infrastructure Setup (10 minutes)
**Deliverables:**
- [x] ✅ Unified audio analysis service implemented
- [x] ✅ Word placement system replacing force alignment
- [x] ✅ Update database connection pool configuration
- [x] ✅ Add HTTP client optimization for reuse
- [x] ✅ Verify async support in all target services

**Acceptance Criteria:**
- Unified analysis generates both soundscape and sound effects
- Word placement provides accurate positioning data
- Database supports 25+ concurrent connections
- No regression in analysis quality

### Phase 2: Service Integration & Async Architecture (20 minutes)  
**Deliverables:**
- [x] ✅ Background music service updated to use unified analysis
- [x] ✅ Sound effects service updated to use unified analysis
- [ ] Convert main e2e flow to async architecture
- [ ] Implement parallel audio generation grouping
- [ ] Add service-level error isolation and timeout handling

**Acceptance Criteria:**
- Services use unified analysis output correctly
- Audio generation services execute in parallel
- Individual service failures don't cascade
- Async flow handles concurrent operations properly
- Output quality matches previous implementation

### Phase 3: Orchestrator Development & Error Management (10 minutes)
**Deliverables:**
- [ ] Implement optimized parallel execution flow
- [ ] Integrate comprehensive error handling (timeouts, isolation, recovery)
- [ ] Add performance monitoring and logging

**Acceptance Criteria:**
- Pipeline executes in optimized phases as designed
- Complete error handling strategy implemented
- Performance metrics captured during execution
- Error scenarios handled gracefully

### Phase 4: End-to-End Testing & Validation (5 minutes)
**Deliverables:**
- [ ] Execute optimized parallel pipeline end-to-end
- [ ] Validate output quality matches sequential version
- [ ] Confirm 131+ second time improvement achieved

**Acceptance Criteria:**
- Total pipeline time reduced by 30-35%
- Resource usage within acceptable limits
- All error scenarios tested and handled properly

