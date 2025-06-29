# Midsummerr Webhook Removal - Cursor AI Implementation Tasks

## 🎯 Goal
Remove webhook complexity and implement parallel processing using Promise.all() for faster, more reliable audio generation.

## 📋 Task List

### Phase 1: Speech Generation Refactor
**Priority: HIGH** - This is your core revenue feature

#### Task 1.1: Replace Batch Processing with Promise.all()
**File:** `services/speech_generation.py`
**Location:** Find the batch processing loop around line 100-150

**Cursor Prompt:**
```
Replace the existing batch processing loop with async Promise.all() pattern. 
Remove all webhook-related code and implement parallel TTS generation for utterances.
Keep error handling but simplify the retry mechanism.
```

**What to change:**
- [ ] Remove `while retry_count < MAX_RETRIES:` loop complexity
- [ ] Replace sequential batch processing with parallel Promise.all()
- [ ] Remove webhook prediction creation calls
- [ ] Keep the utterance creation logic intact
- [ ] Simplify error handling to basic try/catch

#### Task 1.2: Update Speech Generation Service Interface
**File:** `services/speech_generation.py`
**Location:** Main function signatures

**Cursor Prompt:**
```
Modify the main speech generation function to return results directly instead of 
triggering webhooks. Ensure the function is fully async and returns completed audio data.
```

**What to change:**
- [ ] Remove webhook return statements
- [ ] Return actual audio data instead of prediction IDs
- [ ] Update function signatures to be async/await compatible

### Phase 2: Sound Effects Refactor
**Priority: MEDIUM** - Secondary feature but affects user experience

#### Task 2.1: Parallel Sound Effects Generation
**File:** `services/sound_effects.py`
**Location:** `generate_and_store_effect` function

**Cursor Prompt:**
```
Replace webhook-based sound effect generation with direct API calls using Promise.all().
Generate multiple sound effects in parallel and store results immediately.
```

**What to change:**
- [ ] Remove `create_webhook_prediction` calls
- [ ] Implement parallel generation for multiple effects
- [ ] Direct storage of audio results
- [ ] Remove webhook callback handling

#### Task 2.2: Update Sound Effects Analysis
**File:** `services/sound_effects.py`
**Location:** Effect analysis and generation workflow

**Cursor Prompt:**
```
Streamline the sound effects workflow to generate and store effects immediately
after analysis, without webhook delays.
```

### Phase 3: Background Music Refactor
**Priority: LOW** - Nice-to-have feature

#### Task 3.1: Direct Background Music Generation
**File:** `services/background_music.py`
**Location:** Main generation function

**Cursor Prompt:**
```
Convert background music generation from webhook-based to direct API calls.
Handle the longer generation time with proper timeout and progress indication.
```

**What to change:**
- [ ] Remove webhook prediction setup
- [ ] Implement direct Replicate API calls with polling
- [ ] Add timeout handling for long-running generations
- [ ] Return audio data directly

### Phase 4: API Endpoint Updates
**Priority: HIGH** - Frontend depends on these

#### Task 4.1: Update Audio Generation Endpoints
**File:** `api/endpoints/audio.py`
**Location:** All audio generation endpoints

**Cursor Prompt:**
```
Update all audio generation endpoints to return completed results instead of 
webhook prediction IDs. Remove webhook status checking endpoints.
```

**What to change:**
- [ ] `/api/audio/text/{text_id}/generate` - return completed audio
- [ ] `/api/sound-effects/analyze/{text_id}` - return generated effects
- [ ] `/api/background-music/{text_id}/process` - return completed music
- [ ] Remove webhook status endpoints

#### Task 4.2: Combine Export Audio Updates
**File:** `services/combine_export_audio.py`
**Location:** Final audio combination logic

**Cursor Prompt:**
```
Update the final audio combination to work with directly available audio data
instead of checking for webhook completion status.
```

### Phase 5: Database Cleanup
**Priority: MEDIUM** - Clean up unused code

#### Task 5.1: Remove Webhook Tables/Fields
**File:** `db/models.py`
**Location:** Database model definitions

**Cursor Prompt:**
```
Remove any database fields related to webhook prediction IDs and status tracking.
Clean up unused webhook-related columns.
```

#### Task 5.2: Update CRUD Operations
**File:** `db/crud.py`
**Location:** Database operations

**Cursor Prompt:**
```
Remove CRUD operations related to webhook prediction management and status updates.
```

### Phase 6: Remove Webhook Infrastructure
**Priority: LOW** - Clean up unused code

#### Task 6.1: Remove Webhook Endpoints
**File:** `api/endpoints/webhooks.py` (if exists)

**Cursor Prompt:**
```
Delete webhook endpoint handlers since we're moving to direct API calls.
```

#### Task 6.2: Clean Up Webhook Utilities
**File:** Search for "webhook" across codebase

**Cursor Prompt:**
```
Find and remove all webhook-related utility functions, imports, and configurations.
```

## 🔧 Implementation Order

1. **Start with Task 1.1** - Speech generation is your core feature
2. **Test thoroughly** - Ensure speech generation works before moving on
3. **Continue with Task 4.1** - Update the API endpoints
4. **Move to Phase 2** - Sound effects (secondary priority)
5. **Finish with cleanup** - Phases 5 & 6

## ⚠️ Important Notes

### Before Starting:
- [ ] Create a backup branch: `git checkout -b remove-webhooks-backup`
- [ ] Test current functionality to establish baseline
- [ ] Document current webhook URLs (in case rollback needed)

### During Implementation:
- [ ] Test each service individually after changes
- [ ] Keep the database models intact until Phase 5
- [ ] Monitor API response times to ensure performance improvement

### Success Metrics:
- [ ] Reduced API response time (should be 2-5x faster)
- [ ] Simplified error handling and debugging
- [ ] Fewer moving parts in the system
- [ ] Same audio quality output

## 🚨 Risk Mitigation

**If something breaks:**
1. Revert to backup branch
2. Test one service at a time
3. Keep original webhook code commented out (don't delete immediately)

**Performance concerns:**
- Monitor API rate limits during parallel calls
- Implement exponential backoff if hitting rate limits
- Consider chunking very large texts

## 📝 Testing Checklist

After each phase:
- [ ] Upload a test book
- [ ] Generate complete audio
- [ ] Verify audio quality matches previous output
- [ ] Check API response times
- [ ] Test error scenarios (invalid input, API failures)

---

**Remember:** This is an MVP optimization. Focus on getting it working reliably first, then optimize further. The goal is to ship faster and debug easier.