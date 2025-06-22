#!/usr/bin/env python3
"""
Debug script to thoroughly test voice generation and understand the generation_id issue.
"""
import asyncio
import os
import sys

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from hume import AsyncHumeClient
from hume.tts import PostedUtterance

async def debug_voice_generation_detailed():
    """Debug voice generation with detailed logging"""
    
    # Get API key
    api_key = os.getenv("HUME_API_KEY")
    if not api_key:
        print("❌ HUME_API_KEY not found in environment")
        return False
    
    print(f"🔑 Using API key: {api_key[:10]}...")
    
    # Initialize client
    hume_client = AsyncHumeClient(api_key=api_key)
    
    try:
        print("🎙️ Testing voice generation with detailed chunk analysis...")
        
        # Create utterance like the failing code
        utterance = PostedUtterance(
            text="Hello, I am Milo.",
            description="A friendly character"
        )
        
        print(f"📝 Utterance: {utterance.text}")
        print(f"📝 Description: {utterance.description}")
        
        # Create streaming request
        tts_stream = hume_client.tts.synthesize_json_streaming(
            utterances=[utterance]
        )
        
        print("📡 Stream created, examining all chunks...")
        
        generation_id = None
        chunk_count = 0
        
        async for chunk in tts_stream:
            chunk_count += 1
            print(f"\n📦 Chunk {chunk_count}:")
            print(f"   Type: {type(chunk)}")
            
            # Check all attributes
            if hasattr(chunk, "generation_id"):
                chunk_gen_id = chunk.generation_id
                print(f"   ✅ Has generation_id: {chunk_gen_id}")
                print(f"   ✅ generation_id type: {type(chunk_gen_id)}")
                print(f"   ✅ generation_id length: {len(str(chunk_gen_id))}")
                print(f"   ✅ generation_id bool: {bool(chunk_gen_id)}")
                
                if chunk_gen_id and not generation_id:
                    generation_id = chunk_gen_id
                    print(f"   🎯 Selected this generation_id!")
            else:
                print(f"   ❌ No generation_id attribute")
            
            # Check other useful attributes
            for attr in ['audio', 'snippet_id', 'text', 'chunk_index']:
                if hasattr(chunk, attr):
                    value = getattr(chunk, attr)
                    print(f"   📋 {attr}: {type(value)} (len: {len(str(value)) if value else 0})")
            
            # Only look at first few chunks to avoid spam
            if chunk_count >= 5:
                print(f"   ... (stopping after {chunk_count} chunks)")
                break
        
        print(f"\n🔍 Final analysis:")
        print(f"   📊 Total chunks examined: {chunk_count}")
        print(f"   🎯 Selected generation_id: {generation_id}")
        print(f"   ✅ generation_id valid: {bool(generation_id)}")
        
        if generation_id:
            print(f"\n🎉 SUCCESS: Found valid generation_id: {generation_id}")
            return True
        else:
            print(f"\n❌ FAILURE: No valid generation_id found")
            return False
            
    except Exception as e:
        print(f"❌ Error during debug: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_voice_generation_detailed())
    print(f"\nTest {'PASSED' if success else 'FAILED'}") 