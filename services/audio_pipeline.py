#!/usr/bin/env python3
"""
Audio Pipeline Service (Track 2)

Audio Analysis → Background Music || Sound Effects → Webhook Wait
Focused on timing measurement with webhook completion tracking.
"""

import asyncio
import time
from typing import Dict, Any

from services.pipeline_orchestration import (
    PipelineConfig, ServerManager, APIClient, wait_for_audio_completion, logger
)


class AudioPipelineSteps:
    """Audio pipeline step implementations"""
    
    def __init__(self, api_client: APIClient, config: PipelineConfig):
        self.api_client = api_client
        self.config = config

    async def run_audio_analysis(self, text_id: int) -> bool:
        """Run audio analysis"""
        print("🎵 Running audio analysis...")
        step_start = time.time()
        
        try:
            response = await self.api_client.make_request("POST", f"/api/audio-analysis/{text_id}/analyze")
            if response.status_code in [200, 202]:
                elapsed = time.time() - step_start
                print(f"✅ Audio analysis completed in {elapsed:.2f}s")
                return True
            else:
                print(f"❌ Audio analysis failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Audio analysis error: {str(e)}")
            return False

    async def run_bg_music_generation(self, text_id: int) -> bool:
        """Run background music generation"""
        print("🎼 Running background music generation...")
        step_start = time.time()
        
        try:
            response = await self.api_client.make_request("POST", f"/api/background-music/{text_id}/process?force=true")
            if response.status_code in [200, 202]:
                elapsed = time.time() - step_start
                print(f"✅ Background music generation triggered in {elapsed:.2f}s")
                return True
            else:
                print(f"❌ Background music generation failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Background music generation error: {str(e)}")
            return False

    async def run_sfx_generation(self, text_id: int) -> bool:
        """Run sound effects generation"""
        print("🔊 Running sound effects generation...")
        step_start = time.time()
        
        try:
            response = await self.api_client.make_request("POST", f"/api/sound-effects/text/{text_id}/generate?force=true")
            if response.status_code in [200, 202]:
                elapsed = time.time() - step_start
                print(f"✅ Sound effects generation triggered in {elapsed:.2f}s")
                return True
            else:
                print(f"❌ Sound effects generation failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Sound effects generation error: {str(e)}")
            return False


class AudioPipelineOrchestrator:
    """Audio pipeline orchestrator"""
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.server_manager = ServerManager(self.config)
        self.api_client = APIClient(self.config)
        self.steps = AudioPipelineSteps(self.api_client, self.config)

    async def run_audio_pipeline(self, text_id: int) -> Dict[str, Any]:
        """Run the audio pipeline track"""
        print(f"\n🚀 Starting Audio Pipeline for text {text_id}")
        print("🎯 Pipeline: Audio Analysis → (Background Music || Sound Effects) → Webhook Wait")
        
        results = {}
        pipeline_start = time.time()
        
        # Step 1: Audio analysis
        audio_analysis_start = time.time()
        if not await self.steps.run_audio_analysis(text_id):
            results["status"] = "FAILED"
            results["error"] = "audio_analysis_failed"
            return results
        results["audio_analysis_time"] = time.time() - audio_analysis_start
        
        # Step 2: Parallel audio generation
        print("🚀 Running background music and sound effects in parallel...")
        parallel_start = time.time()
        
        bg_task = self.steps.run_bg_music_generation(text_id)
        sfx_task = self.steps.run_sfx_generation(text_id)
        
        bg_triggered, sfx_triggered = await asyncio.gather(bg_task, sfx_task)
        results["audio_generation_time"] = time.time() - parallel_start
        
        # If neither audio generation was triggered successfully, fail
        if not (bg_triggered or sfx_triggered):
            results["status"] = "FAILED"
            results["error"] = "no_audio_generation_triggered"
            results["bg_music_triggered"] = False
            results["sfx_triggered"] = False
            results["bg_music_completed"] = False
            results["sfx_completed"] = False
            results["total_duration"] = time.time() - pipeline_start
            return results
        
        # Step 3: Wait for webhook completion for only the triggered audio
        print("\n🔗 Pipeline now waiting for Replicate webhooks to deliver audio...")
        webhook_start = time.time()
        
        completion_results = await wait_for_audio_completion(
            text_id, bg_triggered, sfx_triggered, self.config.webhook_timeout
        )
        results["webhook_wait_time"] = completion_results["completion_time"]
        
        # Final status determination: pipeline succeeds if webhooks completed for what was triggered
        bg_final = completion_results["bg_music_completed"] if bg_triggered else True  # True if not needed
        sfx_final = completion_results["sfx_completed"] if sfx_triggered else True     # True if not needed
        
        if bg_final and sfx_final:
            results["status"] = "SUCCESS"
        else:
            results["status"] = "PARTIAL_SUCCESS"
            if bg_triggered and not completion_results["bg_music_completed"]:
                results["error"] = "background_music_webhook_failed"
            elif sfx_triggered and not completion_results["sfx_completed"]:
                results["error"] = "sound_effects_webhook_failed"
            else:
                results["error"] = "webhook_completion_failed"
        
        # Final results
        results["total_duration"] = time.time() - pipeline_start
        results["bg_music_triggered"] = bg_triggered
        results["sfx_triggered"] = sfx_triggered
        results["bg_music_completed"] = completion_results["bg_music_completed"]
        results["sfx_completed"] = completion_results["sfx_completed"]
        
        return results


# Main service function for CLI wrapper
async def run_audio_pipeline(text_id: int, ensure_server: bool = True) -> bool:
    """
    Run the audio pipeline for a given text_id.
    
    Args:
        text_id: The ID of the text to process
        ensure_server: Whether to ensure server is running
        
    Returns:
        bool: True if pipeline completed successfully
    """
    orchestrator = AudioPipelineOrchestrator()
    
    try:
        # Ensure server is running if requested
        if ensure_server and not orchestrator.server_manager.ensure_running():
            logger.error("Failed to start FastAPI server")
            return False
        
        # Run the pipeline
        results = await orchestrator.run_audio_pipeline(text_id)
        
        # Log results
        if results["status"] == "SUCCESS":
            logger.info(f"✅ Audio pipeline completed successfully in {results['total_duration']:.2f}s")
            if results.get("webhook_wait_time"):
                logger.info(f"🔗 Webhook wait time: {results['webhook_wait_time']:.2f}s")
            return True
        else:
            logger.error(f"❌ Audio pipeline failed: {results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Audio pipeline error: {str(e)}")
        return False
    finally:
        if ensure_server:
            orchestrator.server_manager.cleanup() 