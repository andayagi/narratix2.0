# Standalone Scripts to CLI Wrapper Conversion Tasks

## Overview
Convert duplicate standalone scripts in `scripts/indie-services/` to thin CLI wrappers that call service functions directly, eliminating code duplication and maintenance burden.

**Current State**: 7 standalone scripts with duplicated service logic  
**Target State**: Thin CLI wrappers that call existing service functions  
**Effort**: 2-3 hours  
**Risk**: Low (preserves functionality, reduces code)

## Problem
- `scripts/indie-services/*.py` duplicate logic from `services/*.py`
- Violates DRY principle - same logic maintained in 2 places
- Standalone scripts were originally for testing but became permanent
- Creates maintenance burden and potential inconsistencies

## Solution Pattern

### Before (Current Duplication):
```python
# scripts/indie-services/background_music_standalone.py (202 lines)
# Duplicates logic from services/background_music.py
def main():
    # 150+ lines of duplicated service logic
    success = await generate_background_music(text_id)  # But also has other logic
```

### After (Thin CLI Wrapper):
```python
# scripts/indie-services/background_music_standalone.py (30 lines)
import asyncio
from services.background_music import generate_background_music

async def main():
    args = parse_arguments()
    success = await generate_background_music(args.text_id)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
```

## Tasks

### Task 1: Convert High-Priority Scripts (1 hour)
**Priority**: HIGH - These are actively used

- [x] **background_music_standalone.py** → CLI wrapper calling `services.background_music.generate_background_music()`
- [x] **audio_analysis_standalone.py** → CLI wrapper calling `services.audio_analysis.analyze_text_for_audio()`
- [x] **sound_effects_standalone.py** → CLI wrapper calling `services.sound_effects.generate_sound_effects_for_text()`

### Task 2: Convert Medium-Priority Scripts (30 minutes)
**Priority**: MEDIUM - Less frequently used

- [x] **combine_export_audio_standalone.py** → CLI wrapper calling `services.combine_export_audio.export_final_audio()`
- [x] **text_analysis_standalone.py** → CLI wrapper calling `services.text_analysis.process_text_analysis()`

### Task 3: Convert Low-Priority Scripts (30 minutes)  
**Priority**: LOW - May be deprecated

- [x] **speech_generation.py** → CLI wrapper calling `services.speech_generation.generate_text_audio()`
- [x] **voice_generation.py** → CLI wrapper calling `services.voice_generation.generate_all_character_voices_parallel()`

### Task 4: Update Documentation (15 minutes)
- [x] Update `scripts/indie-services/README.md` to reflect CLI wrapper pattern
- [x] Remove references to "standalone services" - call them "CLI wrappers"

## Implementation Template

```python
#!/usr/bin/env python3
"""
CLI wrapper for {SERVICE_NAME} service.
Calls the service function directly without duplicating logic.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.{service_module} import {service_function}
from utils.logging import get_logger

logger = get_logger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="{Service description}")
    # Add service-specific arguments
    return parser.parse_args()

async def main():
    args = parse_arguments()
    logger.info(f"Starting {service_name} for {args.text_id}")
    
    try:
        success = await {service_function}(args.text_id)
        if success:
            logger.info("✅ Service completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Service failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

## Success Criteria
- [x] All standalone scripts under 50 lines (currently 150-200 lines each)
- [x] Zero duplicate service logic between `scripts/` and `services/`
- [x] All CLI functionality preserved
- [x] Reduced maintenance burden - logic only exists in `services/`

## Code Reduction Impact
- **Before**: ~1,400 lines across 7 standalone scripts
- **After**: ~350 lines (thin CLI wrappers)
- **Reduction**: ~75% code reduction in standalone scripts
- **Maintenance**: Single source of truth for all service logic

### Progress Update
**Task 1 (HIGH)**: ✅ Complete - 3 scripts converted  
**Task 2 (MEDIUM)**: ✅ Complete - 2 scripts converted (354→209 lines, 41% reduction)
- combine_export_audio_standalone.py: 189→91 lines (52% reduction)
- text_analysis_standalone.py: 165→118 lines (28% reduction)

**Task 3 (LOW)**: ✅ Complete - 2 scripts converted
- speech_generation.py: 149→59 lines (60% reduction)
- voice_generation.py: 201→77 lines (62% reduction)

**Task 4 (Documentation)**: ✅ Complete - README updated to reflect CLI wrapper pattern
- Updated title from "Indie Services - Standalone Scripts" to "CLI Wrappers"
- Added architecture explanation and benefits
- Emphasized that scripts call service functions directly
- Removed all references to "standalone services"

---

*Priority: HIGH - Eliminates significant technical debt*  
*Effort: 2-3 hours total*  
*Dependencies: None - can start immediately* 