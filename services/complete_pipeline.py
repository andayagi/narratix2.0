#!/usr/bin/env python3
"""
Complete E2E Pipeline Service

Orchestrates the complete text-to-audio pipeline:
Track 1: Text Analysis → Voice Generation → Speech Generation
Track 2: Audio Analysis → (Background Music || Sound Effects)
Final: Audio Export (triggered when all webhooks complete)
"""

import asyncio
import time
from typing import Dict, Any, Optional

from services.pipeline_orchestration import (
    PipelineConfig, ServerManager, APIClient, TextManager, PipelineDataManager,
    wait_for_audio_completion, logger
)


class CompletePipelineSteps:
    """Complete pipeline step implementations"""
    
    def __init__(self, api_client: APIClient, config: PipelineConfig):
        self.api_client = api_client
        self.config = config

    # Speech Track Steps
    async def run_text_analysis(self, text_id: int) -> bool:
        """Run text analysis and wait for completion."""
        print("📝 Running text analysis...")
        try:
            start_response = await self.api_client.make_request(
                "POST", f"/api/text-analysis/{text_id}/analyze"
            )
            if start_response.status_code not in [200, 202]:
                print(f"❌ Text analysis failed to start: {start_response.text}")
                return False

            print("⏳ Text analysis started, waiting for completion...")

            # Poll for completion status
            max_wait = 120  # 2 minutes
            poll_interval = 5
            start_time = time.time()

            while time.time() - start_time < max_wait:
                await asyncio.sleep(poll_interval)
                status_response = await self.api_client.make_request(
                    "GET", f"/api/text/{text_id}"
                )
                
                if status_response.status_code == 200:
                    text_data = status_response.json()
                    if text_data.get("analyzed"):
                        print("✅ Text analysis completed")
                        return True
                
                elapsed = time.time() - start_time
                print(f"   ... still analyzing ({elapsed:.0f}s)")

            print("⏰ Timeout waiting for text analysis to complete")
            return False

        except Exception as e:
            print(f"❌ Text analysis error: {str(e)}")
            return False

    async def run_voice_generation(self, text_id: int) -> bool:
        """Run voice generation in parallel for all characters"""
        print("🎙️  Running voice generation...")
        try:
            response = await self.api_client.make_request("GET", f"/api/character/text/{text_id}")
            if response.status_code != 200:
                print("❌ Failed to retrieve characters")
                return False
                
            characters = response.json()
            characters_needing_voices = [c for c in characters if not c.get('provider_id')]
            
            print(f"📊 Voice status: {len(characters)} total characters, {len(characters_needing_voices)} need voices")
            for char in characters:
                has_voice = "✅" if char.get('provider_id') else "❌"
                print(f"   {has_voice} {char['name']}: {char.get('provider_id', 'No voice')}")
            
            if not characters_needing_voices:
                print("✅ All characters already have voices")
                return True
            
            print(f"🚀 Generating voices for {len(characters_needing_voices)} characters in parallel...")
            
            async def generate_voice(character):
                response = await self.api_client.make_request(
                    "POST", f"/api/character/{character['id']}/voice",
                    json={"text_id": text_id}
                )
                success = response.status_code == 200
                print(f"{'✅' if success else '❌'} Voice for {character['name']}: {'Success' if success else 'Failed'}")
                return success
            
            # Execute all voice generations in parallel
            results = await asyncio.gather(*[generate_voice(char) for char in characters_needing_voices])
            success_count = sum(results)
            
            print(f"✅ Voice generation: {success_count}/{len(characters_needing_voices)} successful")
            return success_count == len(characters_needing_voices)
            
        except Exception as e:
            print(f"❌ Voice generation error: {str(e)}")
            return False

    async def run_speech_generation(self, text_id: int) -> bool:
        """Run speech generation"""
        print("🗣️  Running speech generation...")
        try:
            response = await self.api_client.make_request("POST", f"/api/audio/text/{text_id}/generate-segments")
            if response.status_code == 200:
                print("✅ Speech generation completed")
                await asyncio.sleep(self.config.post_speech_generation_wait)  # Wait for files to be saved
                return True
            else:
                print(f"❌ Speech generation failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Speech generation error: {str(e)}")
            return False

    # Audio Track Steps
    async def run_audio_analysis(self, text_id: int) -> bool:
        """Run audio analysis"""
        print("🎵 Running audio analysis...")
        try:
            response = await self.api_client.make_request("POST", f"/api/audio-analysis/{text_id}/analyze")
            if response.status_code in [200, 202]:
                print("✅ Audio analysis completed")
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
        try:
            response = await self.api_client.make_request("POST", f"/api/background-music/{text_id}/process?force=true")
            if response.status_code in [200, 202]:
                print("✅ Background music generation triggered")
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
        try:
            response = await self.api_client.make_request("POST", f"/api/sound-effects/text/{text_id}/generate?force=true")
            if response.status_code in [200, 202]:
                print("✅ Sound effects generation triggered")
                return True
            else:
                print(f"❌ Sound effects generation failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Sound effects generation error: {str(e)}")
            return False

    async def run_final_audio(self, text_id: int) -> Optional[str]:
        """Run final audio combining"""
        print("🎬 Running final audio export...")
        try:
            response = await self.api_client.make_request("POST", f"/api/export/{text_id}/final-audio")
            if response.status_code in [200, 202]:
                try:
                    response_data = response.json()
                    output_path = response_data.get("data", {}).get("audio_file")
                    print(f"✅ Final audio export completed: {output_path}")
                    return output_path
                except:
                    print("✅ Final audio export completed")
                    return f"output/final_audio_{text_id}.mp3"
            else:
                print(f"❌ Final audio export failed: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Final audio export error: {str(e)}")
            return None


class CompletePipelineOrchestrator:
    """Complete pipeline orchestrator"""
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.server_manager = ServerManager(self.config)
        self.api_client = APIClient(self.config)
        self.text_manager = TextManager(self.api_client)
        self.data_manager = PipelineDataManager()
        self.steps = CompletePipelineSteps(self.api_client, self.config)

    async def run_complete_pipeline(self, text_id: int) -> Dict[str, Any]:
        """Run the complete parallel pipeline"""
        print(f"\n🚀 Starting complete pipeline for text {text_id}")
        print("🎯 Pipeline structure:")
        print("   Track 1: Text Analysis → Voice Generation → Speech Generation")
        print("   Track 2: Audio Analysis → (Background Music || Sound Effects)")
        print("   🔗 Webhook-triggered: Audio generation waits for Replicate webhooks")
        print("   Final: Audio Export (triggered immediately when all webhooks complete)")
        
        results = {}
        start_time = time.time()
        
        # Step 1: Reset all data
        if not await self.data_manager.reset_pipeline_data(text_id):
            results["status"] = "FAILED"
            results["error"] = "Failed to reset pipeline data"
            return results
        
        # Step 2: Run parallel tracks
        async def speech_track():
            """Track 1: Text → Voice → Speech"""
            print("\n🎤 Starting Speech Track...")
            
            # Text analysis
            if not await self.steps.run_text_analysis(text_id):
                return {"speech_track": False, "error": "text_analysis_failed"}
            
            # Voice generation (parallel)
            if not await self.steps.run_voice_generation(text_id):
                return {"speech_track": False, "error": "voice_generation_failed"}
            
            # Speech generation
            if not await self.steps.run_speech_generation(text_id):
                return {"speech_track": False, "error": "speech_generation_failed"}
            
            print("✅ Speech Track completed")
            return {"speech_track": True}
        
        async def audio_track():
            """Track 2: Audio Analysis → (BG Music || SFX)"""
            print("\n🎵 Starting Audio Track...")
            
            # Audio analysis
            if not await self.steps.run_audio_analysis(text_id):
                return {"audio_track": False, "error": "audio_analysis_failed"}
            
            # Parallel audio generation
            print("🚀 Running background music and sound effects in parallel...")
            bg_task = self.steps.run_bg_music_generation(text_id)
            sfx_task = self.steps.run_sfx_generation(text_id)
            
            bg_result, sfx_result = await asyncio.gather(bg_task, sfx_task)
            
            if bg_result or sfx_result:
                print("\n🔗 Pipeline now waiting for Replicate webhooks to deliver audio...")
                print("⏳ Terminal will remain open until all webhooks complete")
                
                # Wait for completion using webhook-triggered approach
                completion_results = await wait_for_audio_completion(text_id, bg_result, sfx_result, self.config.webhook_timeout)
                final_bg = completion_results["bg_music_completed"] if bg_result else True
                final_sfx = completion_results["sfx_completed"] if sfx_result else True
                
                if final_bg and final_sfx:
                    print("✅ Audio Track completed")
                    return {"audio_track": True, "webhook_wait_time": completion_results.get("completion_time", 0)}
                else:
                    return {"audio_track": False, "error": "audio_completion_failed", "webhook_wait_time": completion_results.get("completion_time", 0)}
            else:
                return {"audio_track": False, "error": "audio_generation_failed"}
        
        # Run both tracks in parallel
        print("\n🚀 Running Speech Track || Audio Track in parallel...")
        track_results = await asyncio.gather(speech_track(), audio_track())
        
        # Process results
        speech_result, audio_result = track_results
        results.update(speech_result)
        results.update(audio_result)
        
        # Check if both tracks succeeded
        if not (speech_result.get("speech_track") and audio_result.get("audio_track")):
            results["status"] = "FAILED"
            results["error"] = f"Track failures: {speech_result.get('error', 'none')}, {audio_result.get('error', 'none')}"
            return results
        
        # Step 3: Final audio export
        print("\n🎬 Running final audio export...")
        output_path = await self.steps.run_final_audio(text_id)
        
        # Final results
        end_time = time.time()
        results["status"] = "SUCCESS" if output_path else "PARTIAL_SUCCESS"
        results["duration"] = end_time - start_time
        results["webhook_wait_time"] = audio_result.get("webhook_wait_time", 0)
        results["output_path"] = output_path
        
        return results


# Main service function for CLI wrapper
async def run_complete_pipeline(text_id: Optional[int] = None, ensure_server: bool = True) -> bool:
    """
    Run the complete E2E pipeline.
    
    Args:
        text_id: The ID of the text to process (if None, creates from input file)
        ensure_server: Whether to ensure server is running
        
    Returns:
        bool: True if pipeline completed successfully
    """
    orchestrator = CompletePipelineOrchestrator()
    
    try:
        # Ensure server is running if requested
        if ensure_server and not orchestrator.server_manager.ensure_running():
            logger.error("Failed to start FastAPI server")
            return False
        
        # Get or create text if needed
        if text_id is None:
            text_id = await orchestrator.text_manager.get_or_create_text()
            if not text_id:
                logger.error("Failed to get text_id")
                return False
        
        # Run the pipeline
        results = await orchestrator.run_complete_pipeline(text_id)
        
        # Log results
        if results["status"] == "SUCCESS":
            logger.info(f"✅ Complete pipeline completed successfully in {results['duration']:.2f}s")
            if results.get("webhook_wait_time"):
                logger.info(f"🔗 Webhook wait time: {results['webhook_wait_time']:.2f}s")
            if results.get("output_path"):
                logger.info(f"📄 Output: {results['output_path']}")
            return True
        else:
            logger.error(f"❌ Complete pipeline failed: {results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Complete pipeline error: {str(e)}")
        return False
    finally:
        if ensure_server:
            orchestrator.server_manager.cleanup() 