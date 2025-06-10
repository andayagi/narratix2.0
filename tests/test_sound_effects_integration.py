"""
Integration test for sound effects service using real APIs
"""
import pytest
import os
import sys
import json
import base64
from datetime import datetime

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.logging import SessionLogger
SessionLogger.start_session(f"test_sound_effects_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

from db import models, crud
from utils.config import settings
from services.sound_effects import (
    analyze_text_for_sound_effects,
    generate_and_store_effect,
    delete_existing_sound_effects
)

# Skip tests if required API keys are not available
if not settings.ANTHROPIC_API_KEY or len(settings.ANTHROPIC_API_KEY) < 10:
    pytest.skip("Valid ANTHROPIC_API_KEY required for sound effects integration test", allow_module_level=True)

# Test configuration
TEST_TEXT_ID = 39  # Using text_id=39 as requested

@pytest.fixture(scope="module")
def test_output_dir():
    """Create output directory for test results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(PROJECT_ROOT, "tests", "output", "sound_effects_integration", timestamp)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

@pytest.fixture
def test_text_39(db_session):
    """Get text_id=39 from database"""
    text = crud.get_text(db_session, TEST_TEXT_ID)
    if not text:
        pytest.skip(f"Text with ID {TEST_TEXT_ID} not found in database")
    return text

class TestSoundEffectsIntegration:
    """Integration tests for sound effects service with real APIs"""

    @pytest.mark.integration
    def test_analyze_text_for_sound_effects_real_api(self, db_session, test_text_39, test_output_dir):
        """Test complete sound effects analysis with real Claude API"""
        print(f"\n=== Testing Sound Effects Analysis for Text ID {TEST_TEXT_ID} ===")
        print(f"Text content preview: {test_text_39.content[:100]}...")
        
        # Clean up any existing sound effects for this text to start fresh using the service method
        deleted_count = delete_existing_sound_effects(db_session, TEST_TEXT_ID)
        print(f"Cleaned up {deleted_count} existing sound effects using service method")
        
        # Run sound effects analysis
        print("Running Claude API analysis...")
        effects = analyze_text_for_sound_effects(db_session, TEST_TEXT_ID)
        
        # Save analysis results
        analysis_output = {
            "description": "Sound effects analysis results using real Claude API",
            "text_id": TEST_TEXT_ID,
            "text_content": test_text_39.content,
            "force_alignment_available": test_text_39.word_timestamps is not None,
            "word_timestamps_count": len(test_text_39.word_timestamps) if test_text_39.word_timestamps else 0,
            "effects_identified": len(effects),
            "effects": effects,
            "timestamp": datetime.now().isoformat()
        }
        
        # Export 1: Claude analysis to test_output_dir
        claude_analysis_file = os.path.join(test_output_dir, f"claude_analysis_text_{TEST_TEXT_ID}.json")
        with open(claude_analysis_file, 'w') as f:
            json.dump(analysis_output, f, indent=2)
        print(f"✓ Claude analysis exported to: {claude_analysis_file}")
        
        output_file = os.path.join(test_output_dir, "1_claude_analysis_results.json")
        with open(output_file, 'w') as f:
            json.dump(analysis_output, f, indent=2)
        
        print(f"✓ Analysis completed: {len(effects)} effects identified")
        print(f"✓ Results saved to: {output_file}")
        
        # Verify effects were stored in database
        stored_effects = crud.get_sound_effects_by_text(db_session, TEST_TEXT_ID)
        assert len(stored_effects) == len(effects)
        print(f"✓ {len(stored_effects)} effects stored in database")
        
        # Verify effect structure
        if stored_effects:
            effect = stored_effects[0]
            assert effect.effect_name is not None
            assert effect.start_word is not None
            assert effect.prompt is not None
            assert effect.text_id == TEST_TEXT_ID
            print(f"✓ Effect structure validated: {effect.effect_name}")
            
            # Display all effects
            for i, effect in enumerate(stored_effects, 1):
                print(f"  {i}. {effect.effect_name}: {effect.start_word} -> {effect.end_word}")
                print(f"     Timing: {effect.start_time}s - {effect.end_time}s")
                print(f"     Prompt: {effect.prompt[:60]}...")
        
        return stored_effects

    @pytest.mark.integration
    def test_generate_sound_effect_audio_real_api(self, db_session, test_output_dir):
        """Test audio generation for sound effects with real AudioX API"""
        print(f"\n=== Testing Sound Effect Audio Generation ===")
        
        # Get sound effects for text_id=39
        stored_effects = crud.get_sound_effects_by_text(db_session, TEST_TEXT_ID)
        if not stored_effects:
            pytest.skip("No sound effects available for audio generation test. Run analysis test first.")
        
        print(f"Found {len(stored_effects)} sound effects to generate audio for")
        
        generation_results = []
        audio_exports = []
        
        # Find the effect with rank=1 (most important according to Claude)
        rank_1_effect = None
        for effect in stored_effects:
            if effect.rank == 1:
                rank_1_effect = effect
                break
        
        if not rank_1_effect:
            pytest.skip("No sound effect with rank=1 found. Claude should have ranked effects.")
        
        print(f"\nGenerating audio for rank #1 effect: {rank_1_effect.effect_name}")
        print(f"Prompt: {rank_1_effect.prompt}")
        
        # Record initial state
        initial_audio_length = len(rank_1_effect.audio_data_b64) if rank_1_effect.audio_data_b64 else 0
        
        try:
            # Generate audio
            generate_and_store_effect(db_session, rank_1_effect.effect_id)
            
            # Refresh from database
            db_session.refresh(rank_1_effect)
            
            # Verify audio was generated
            final_audio_length = len(rank_1_effect.audio_data_b64) if rank_1_effect.audio_data_b64 else 0
            audio_generated = final_audio_length > 0  # Real audio should be more than empty
            
            # Export audio to test_output_dir (only if real audio exists)
            if rank_1_effect.audio_data_b64 and len(rank_1_effect.audio_data_b64) > 0:
                audio_filename = f"sound_effect_{rank_1_effect.effect_id}_{rank_1_effect.effect_name}.wav"
                audio_file_path = os.path.join(test_output_dir, audio_filename)
                
                try:
                    audio_data = base64.b64decode(rank_1_effect.audio_data_b64)
                    with open(audio_file_path, 'wb') as f:
                        f.write(audio_data)
                    audio_exports.append(audio_file_path)
                    print(f"✓ Audio exported to: {audio_file_path}")
                    print(f"  Audio data size: {len(audio_data)} bytes")
                except Exception as e:
                    print(f"✗ Failed to export audio: {e}")
                    print(f"  Audio data length: {len(rank_1_effect.audio_data_b64)} chars")
            else:
                print(f"✗ No audio data generated for {rank_1_effect.effect_name}")
            
            result = {
                "effect_id": rank_1_effect.effect_id,
                "effect_name": rank_1_effect.effect_name,
                "prompt": rank_1_effect.prompt,
                "duration_calculated": rank_1_effect.total_time,
                "audio_generated": audio_generated,
                "audio_data_length": final_audio_length,
                "start_time": rank_1_effect.start_time,
                "end_time": rank_1_effect.end_time,
                "claude_rank": rank_1_effect.rank
            }
            
            generation_results.append(result)
            
            print(f"✓ Audio generation {'successful' if audio_generated else 'failed'}")
            print(f"  Audio data length: {final_audio_length} characters")
            
        except Exception as e:
            print(f"✗ Audio generation failed: {str(e)}")
            result = {
                "effect_id": rank_1_effect.effect_id,
                "effect_name": rank_1_effect.effect_name,
                "error": str(e),
                "audio_generated": False,
                "claude_rank": rank_1_effect.rank
            }
            generation_results.append(result)
        
        # Save generation results
        generation_output = {
            "description": "Sound effect audio generation results using real AudioX API",
            "text_id": TEST_TEXT_ID,
            "effects_processed": len(generation_results),
            "successful_generations": sum(1 for r in generation_results if r.get("audio_generated", False)),
            "audio_files_exported": audio_exports,
            "results": generation_results,
            "timestamp": datetime.now().isoformat()
        }
        
        output_file = os.path.join(test_output_dir, "2_audio_generation_results.json")
        with open(output_file, 'w') as f:
            json.dump(generation_output, f, indent=2)
        
        print(f"\n✓ Audio generation results saved to: {output_file}")
        print(f"✓ Exported {len(audio_exports)} audio files to {test_output_dir}")
        
        # Verify at least some audio was generated - FAIL if none
        successful_generations = sum(1 for r in generation_results if r.get("audio_generated", False))
        print(f"✓ Successfully generated audio for {successful_generations}/{len(generation_results)} effects")
        
        # Test should fail if no audio was actually generated
        assert successful_generations > 0, f"No audio was successfully generated for any of the {len(generation_results)} effects"
        
        return generation_results

    @pytest.mark.integration
    def test_complete_workflow_end_to_end(self, db_session, test_text_39, test_output_dir):
        """Test complete end-to-end workflow from analysis to audio generation"""
        print(f"\n=== Complete End-to-End Sound Effects Workflow Test ===")
        
        workflow_results = {
            "text_id": TEST_TEXT_ID,
            "text_content_length": len(test_text_39.content),
            "force_alignment_available": test_text_39.word_timestamps is not None,
            "workflow_steps": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Step 1: Clean slate using the service method
        print("Step 1: Cleaning up existing sound effects...")
        deleted_count = delete_existing_sound_effects(db_session, TEST_TEXT_ID)
        workflow_results["workflow_steps"].append({
            "step": "cleanup",
            "status": "completed",
            "effects_removed": deleted_count
        })
        
        # Step 2: Analysis
        print("Step 2: Running sound effects analysis...")
        try:
            effects = analyze_text_for_sound_effects(db_session, TEST_TEXT_ID)
            workflow_results["workflow_steps"].append({
                "step": "analysis",
                "status": "completed",
                "effects_identified": len(effects)
            })
            print(f"✓ Analysis completed: {len(effects)} effects identified")
        except Exception as e:
            workflow_results["workflow_steps"].append({
                "step": "analysis",
                "status": "failed",
                "error": str(e)
            })
            print(f"✗ Analysis failed: {str(e)}")
            raise
        
        # Step 3: Audio Generation (for first effect only in end-to-end test)
        if effects:
            print("Step 3: Generating audio for first sound effect...")
            try:
                stored_effects = crud.get_sound_effects_by_text(db_session, TEST_TEXT_ID)
                first_effect = stored_effects[0]
                
                generate_and_store_effect(db_session, first_effect.effect_id)
                db_session.refresh(first_effect)
                
                audio_generated = len(first_effect.audio_data_b64) > 0  # Changed to check for any audio content
                workflow_results["workflow_steps"].append({
                    "step": "audio_generation",
                    "status": "completed" if audio_generated else "failed",
                    "effect_name": first_effect.effect_name,
                    "audio_generated": audio_generated
                })
                print(f"✓ Audio generation {'completed' if audio_generated else 'failed'}")
                
            except Exception as e:
                workflow_results["workflow_steps"].append({
                    "step": "audio_generation", 
                    "status": "failed",
                    "error": str(e)
                })
                print(f"✗ Audio generation failed: {str(e)}")
        
        # Step 4: Export combined speech+sound effects
        print("Step 4: Creating combined speech+sound effects...")
        try:
            # Export 3: Combined speech + sound effects to test_output_dir
            
            # Get the original speech audio (if available)
            speech_audio_b64 = test_text_39.audio_data_b64 if hasattr(test_text_39, 'audio_data_b64') and test_text_39.audio_data_b64 else None
            
            combined_info = {
                "description": "Combined speech and sound effects information",
                "text_id": TEST_TEXT_ID,
                "speech_audio_available": speech_audio_b64 is not None,
                "speech_audio_length": len(speech_audio_b64) if speech_audio_b64 else 0,
                "sound_effects_count": len(stored_effects) if 'stored_effects' in locals() else 0,
                "note": "Actual audio mixing not implemented - this is metadata only",
                "timestamp": datetime.now().isoformat()
            }
            
            combined_file = os.path.join(test_output_dir, f"combined_audio_info_text_{TEST_TEXT_ID}.json")
            with open(combined_file, 'w') as f:
                json.dump(combined_info, f, indent=2)
            
            workflow_results["workflow_steps"].append({
                "step": "combined_export", 
                "status": "completed",
                "info_file": combined_file
            })
            print(f"✓ Combined audio info exported to: {combined_file}")
            
        except Exception as e:
            workflow_results["workflow_steps"].append({
                "step": "combined_export",
                "status": "failed", 
                "error": str(e)
            })
            print(f"✗ Combined export failed: {str(e)}")
        
        # Step 5: Final verification
        print("Step 5: Final verification...")
        final_effects = crud.get_sound_effects_by_text(db_session, TEST_TEXT_ID)
        effects_with_audio = sum(1 for e in final_effects if e.audio_data_b64 and len(e.audio_data_b64) > 100)
        
        workflow_results["final_state"] = {
            "total_effects": len(final_effects),
            "effects_with_audio": effects_with_audio,
            "workflow_success": len(final_effects) > 0 and effects_with_audio > 0  # Restore audio requirement
        }
        
        # Save complete workflow results
        output_file = os.path.join(test_output_dir, "3_complete_workflow_results.json")
        with open(output_file, 'w') as f:
            json.dump(workflow_results, f, indent=2)
        
        print(f"✓ Complete workflow results saved to: {output_file}")
        print(f"✓ Workflow {'SUCCESSFUL' if workflow_results['final_state']['workflow_success'] else 'INCOMPLETE'}")
        
        # Assertions for test validation - restore audio requirement
        assert len(final_effects) > 0, "Should have at least one sound effect"
        assert effects_with_audio > 0, "Should have at least one effect with generated audio"
        
        return workflow_results

if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v", "-s"]) 