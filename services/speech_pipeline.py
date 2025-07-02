#!/usr/bin/env python3
"""
Speech Pipeline Service (Track 1)

Text Analysis → Voice Generation → Speech Generation
Focused on timing measurement without webhook dependencies.
"""

import asyncio
import time
from typing import Dict, Any

from services.pipeline_orchestration import (
    PipelineConfig, ServerManager, APIClient, TextManager, PipelineDataManager, logger
)


class SpeechPipelineSteps:
    """Speech pipeline step implementations"""
    
    def __init__(self, api_client: APIClient, config: PipelineConfig):
        self.api_client = api_client
        self.config = config

    async def run_text_analysis(self, text_id: int) -> bool:
        """Run text analysis and wait for completion."""
        print("📝 Running text analysis...")
        step_start = time.time()
        
        try:
            # Start the analysis (non-blocking)
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
                        elapsed = time.time() - step_start
                        print(f"✅ Text analysis completed in {elapsed:.2f}s")
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
        step_start = time.time()
        
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
                elapsed = time.time() - step_start
                print(f"✅ All characters already have voices ({elapsed:.2f}s)")
                return True
            
            print(f"🚀 Generating voices for {len(characters_needing_voices)} characters in parallel...")
            
            async def generate_voice(character):
                char_start = time.time()
                response = await self.api_client.make_request(
                    "POST", f"/api/character/{character['id']}/voice",
                    json={"text_id": text_id}
                )
                success = response.status_code == 200
                char_elapsed = time.time() - char_start
                print(f"{'✅' if success else '❌'} Voice for {character['name']}: {'Success' if success else 'Failed'} ({char_elapsed:.2f}s)")
                return success
            
            # Execute all voice generations in parallel
            results = await asyncio.gather(*[generate_voice(char) for char in characters_needing_voices])
            success_count = sum(results)
            
            elapsed = time.time() - step_start
            print(f"✅ Voice generation: {success_count}/{len(characters_needing_voices)} successful ({elapsed:.2f}s)")
            return success_count == len(characters_needing_voices)
            
        except Exception as e:
            print(f"❌ Voice generation error: {str(e)}")
            return False

    async def run_speech_generation(self, text_id: int) -> bool:
        """Run speech generation"""
        print("🗣️  Running speech generation...")
        step_start = time.time()
        
        try:
            response = await self.api_client.make_request("POST", f"/api/audio/text/{text_id}/generate-segments")
            if response.status_code == 200:
                elapsed = time.time() - step_start
                print(f"✅ Speech generation completed in {elapsed:.2f}s")
                await asyncio.sleep(self.config.post_speech_generation_wait)  # Wait for files to be saved
                return True
            else:
                print(f"❌ Speech generation failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Speech generation error: {str(e)}")
            return False


class SpeechPipelineOrchestrator:
    """Speech pipeline orchestrator"""
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.server_manager = ServerManager(self.config)
        self.api_client = APIClient(self.config)
        self.text_manager = TextManager(self.api_client)
        self.data_manager = PipelineDataManager()
        self.steps = SpeechPipelineSteps(self.api_client, self.config)

    async def run_speech_pipeline(self, text_id: int) -> Dict[str, Any]:
        """Run the speech pipeline track"""
        print(f"\n🚀 Starting Speech Pipeline for text {text_id}")
        print("🎯 Pipeline: Text Analysis → Voice Generation → Speech Generation")
        
        results = {}
        pipeline_start = time.time()
        
        # Step 1: Reset speech data
        if not await self.data_manager.reset_speech_data(text_id):
            results["status"] = "FAILED"
            results["error"] = "Failed to reset speech pipeline data"
            return results
        
        # Step 2: Text analysis
        text_start = time.time()
        if not await self.steps.run_text_analysis(text_id):
            results["status"] = "FAILED"
            results["error"] = "text_analysis_failed"
            return results
        results["text_analysis_time"] = time.time() - text_start
        
        # Step 3: Voice generation
        voice_start = time.time()
        if not await self.steps.run_voice_generation(text_id):
            results["status"] = "FAILED"
            results["error"] = "voice_generation_failed"
            return results
        results["voice_generation_time"] = time.time() - voice_start
        
        # Step 4: Speech generation
        speech_start = time.time()
        if not await self.steps.run_speech_generation(text_id):
            results["status"] = "FAILED" 
            results["error"] = "speech_generation_failed"
            return results
        results["speech_generation_time"] = time.time() - speech_start
        
        # Final results
        results["status"] = "SUCCESS"
        results["total_duration"] = time.time() - pipeline_start
        
        return results


# Main service function for CLI wrapper
async def run_speech_pipeline(text_id: int, ensure_server: bool = True) -> bool:
    """
    Run the speech pipeline for a given text_id.
    
    Args:
        text_id: The ID of the text to process
        ensure_server: Whether to ensure server is running
        
    Returns:
        bool: True if pipeline completed successfully
    """
    orchestrator = SpeechPipelineOrchestrator()
    
    try:
        # Ensure server is running if requested
        if ensure_server and not orchestrator.server_manager.ensure_running():
            logger.error("Failed to start FastAPI server")
            return False
        
        # Run the pipeline
        results = await orchestrator.run_speech_pipeline(text_id)
        
        # Log results
        if results["status"] == "SUCCESS":
            logger.info(f"✅ Speech pipeline completed successfully in {results['total_duration']:.2f}s")
            return True
        else:
            logger.error(f"❌ Speech pipeline failed: {results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Speech pipeline error: {str(e)}")
        return False
    finally:
        if ensure_server:
            orchestrator.server_manager.cleanup() 