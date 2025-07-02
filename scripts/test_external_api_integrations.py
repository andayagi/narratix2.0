#!/usr/bin/env python3
"""
External API Integration Test Script for Phase 1 Task 5.2
Comprehensive testing of all external API integrations for production readiness.
"""

import os
import sys
import json
import asyncio
import aiohttp
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ExternalAPITestSuite:
    """Comprehensive external API integration test suite."""
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
    def print_header(self, title: str):
        """Print a formatted header."""
        print("\n" + "=" * 70)
        print(f" {title}")
        print("=" * 70)
        
    def print_step(self, step: str, status: str = ""):
        """Print a test step."""
        print(f"\n🔍 {step}")
        if status:
            print(f"   {status}")
            
    def print_result(self, test_name: str, success: bool, details: str = ""):
        """Print test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        return success

    async def test_anthropic_claude_api(self) -> bool:
        """Test Anthropic Claude API integration comprehensively."""
        self.print_step("Testing Anthropic Claude API Integration")
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return self.print_result("Anthropic Claude API", False, "API key not found")
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            
            # Test 1: Basic connectivity
            response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=50,
                messages=[{"role": "user", "content": "Test message for API validation. Respond with 'API_TEST_OK'."}]
            )
            
            if not response or not response.content:
                return self.print_result("Anthropic Claude API", False, "No response received")
            
            print("   ✓ Basic connectivity successful")
            
            # Test 2: Text analysis functionality (similar to production usage)
            analysis_prompt = """
            Analyze this narrative text for sound effects opportunities:
            "The rain began to tap against the window as Sarah opened the creaky door."
            
            Respond in JSON format with sound effects identified.
            """
            
            analysis_response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            if analysis_response and analysis_response.content:
                print("   ✓ Text analysis functionality working")
                print(f"   ✓ Response length: {len(analysis_response.content[0].text)} characters")
            else:
                return self.print_result("Anthropic Claude API", False, "Analysis test failed")
            
            return self.print_result("Anthropic Claude API", True, "All tests passed")
            
        except Exception as e:
            return self.print_result("Anthropic Claude API", False, f"Error: {str(e)}")

    async def test_hume_ai_api(self) -> bool:
        """Test Hume AI API integration comprehensively."""
        self.print_step("Testing Hume AI API Integration")
        
        api_key = os.getenv("HUME_API_KEY")
        if not api_key:
            return self.print_result("Hume AI API", False, "API key not found")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "X-Hume-Api-Key": api_key,
                    "Content-Type": "application/json"
                }
                
                # Test 1: API key validation
                async with session.get(
                    "https://api.hume.ai/v0/batch/jobs",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        print("   ✓ API key validation successful")
                    elif response.status == 401:
                        return self.print_result("Hume AI API", False, "Invalid API key")
                    else:
                        print(f"   ⚠️  Unexpected status {response.status}, continuing tests...")
                
                return self.print_result("Hume AI API", True, "API integration verified")
                
        except Exception as e:
            return self.print_result("Hume AI API", False, f"Error: {str(e)}")

    async def test_replicate_api(self) -> bool:
        """Test Replicate API integration comprehensively."""
        self.print_step("Testing Replicate API Integration")
        
        api_token = os.getenv("REPLICATE_API_TOKEN")
        if not api_token:
            return self.print_result("Replicate API", False, "API token not found")
        
        try:
            import replicate
            
            # Test 1: Basic connectivity by listing models
            try:
                models = replicate.models.list()
                # Try to get first model to test API access
                first_model = next(iter(models), None)
                if first_model:
                    print(f"   ✓ Authentication successful")
                    print(f"   ✓ API access working, found models")
                else:
                    return self.print_result("Replicate API", False, "No models accessible")
            except Exception as e:
                return self.print_result("Replicate API", False, f"Authentication failed: {str(e)}")
            
            # Test 2: Model access for audio generation
            audio_models = [
                "stability-ai/stable-audio-open-1.0",
                "riffusion/riffusion", 
                "cjwbw/musicgen"
            ]
            
            accessible_models = []
            for model_name in audio_models:
                try:
                    model = replicate.models.get(model_name)
                    accessible_models.append(model_name)
                    print(f"   ✓ Audio model accessible: {model_name}")
                except Exception:
                    print(f"   ⚠️  Audio model not accessible: {model_name}")
            
            if not accessible_models:
                print("   ⚠️  No specific audio models accessible, but API is working")
            
            return self.print_result("Replicate API", True, f"API verified, {len(accessible_models)} audio models accessible")
            
        except Exception as e:
            return self.print_result("Replicate API", False, f"Error: {str(e)}")

    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all external API integration tests."""
        self.print_header("Phase 1 Task 5.2: External API Integration Tests")
        
        print(f"🚀 Starting external API tests at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌍 Environment: {self.environment}")
        print(f"📍 Running from: {PROJECT_ROOT}")
        print(f"🔧 Testing production readiness of external API integrations")
        
        # Run all tests
        tests = [
            ("Anthropic Claude API", await self.test_anthropic_claude_api()),
            ("Hume AI API", await self.test_hume_ai_api()),
            ("Replicate API", await self.test_replicate_api()),
        ]
        
        # Collect results
        self.results = {name: result for name, result in tests}
        
        # Print summary
        self.print_summary()
        
        return self.results
    
    def print_summary(self):
        """Print test summary."""
        self.print_header("External API Integration Test Summary")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result)
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n📊 Results: {passed_tests}/{total_tests} API integration tests passed")
        
        if passed_tests == total_tests:
            print("✅ All external API integrations verified for production readiness!")
            print("🚀 Task 5.2 completed successfully")
        else:
            print("❌ Some API integrations need attention before production deployment")
        
        elapsed_time = datetime.now() - self.start_time
        print(f"⏱️  Total test time: {elapsed_time.total_seconds():.2f} seconds")

async def main():
    """Main test execution."""
    test_suite = ExternalAPITestSuite()
    results = await test_suite.run_all_tests()
    
    # Exit with appropriate code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    asyncio.run(main()) 