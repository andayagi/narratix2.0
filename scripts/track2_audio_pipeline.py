#!/usr/bin/env python3
"""
CLI wrapper for Track 2 Audio Pipeline service.
Calls the service function directly without duplicating logic.

Usage:
    python3 scripts/track2_audio_pipeline.py [text_id]
    
Requires existing text_id with completed speech generation.
"""

import argparse
import asyncio
import sys
import signal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.audio_pipeline import run_audio_pipeline
from utils.logging import get_logger
from utils.ngrok_sync import sync_ngrok_url

logger = get_logger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Run Track 2 Audio Pipeline (Audio Analysis → Background Music || Sound Effects)")
    parser.add_argument("text_id", type=int, help="Text ID to process (must have completed speech generation)")
    return parser.parse_args()

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        print("\n🛑 Received interrupt signal, shutting down gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

async def main():
    args = parse_arguments()
    setup_signal_handlers()
    
    print("🎵 Track 2 Audio Pipeline")
    print("=========================")
    
    # Sync ngrok URL at startup
    print("🔗 Syncing ngrok URL...")
    success, ngrok_url = sync_ngrok_url()
    if success and ngrok_url:
        print(f"✅ Using ngrok URL: {ngrok_url}")
    else:
        print("⚠️  Could not sync ngrok URL, using localhost")
    
    try:
        text_id = args.text_id
        logger.info(f"Starting audio pipeline for text {text_id}")
        
        # Run the pipeline service
        success = await run_audio_pipeline(text_id, ensure_server=True)
        
        if success:
            logger.info("✅ Audio pipeline completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Audio pipeline failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 