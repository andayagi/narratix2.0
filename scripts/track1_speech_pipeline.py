#!/usr/bin/env python3
"""
CLI wrapper for Track 1 Speech Pipeline service.
Calls the service function directly without duplicating logic.

Usage:
    python3 scripts/track1_speech_pipeline.py [text_id]
    
If no text_id provided, uses input_interactive_e2e.txt
"""

import argparse
import asyncio
import sys
import signal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.speech_pipeline import run_speech_pipeline
from services.pipeline_orchestration import TextManager, APIClient, PipelineConfig
from utils.logging import get_logger
from utils.ngrok_sync import sync_ngrok_url

logger = get_logger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Run Track 1 Speech Pipeline (Text Analysis → Voice Generation → Speech Generation)")
    parser.add_argument("text_id", type=int, nargs='?', help="Text ID to process (if not provided, creates from input file)")
    return parser.parse_args()

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        print("\n🛑 Received interrupt signal, shutting down gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

async def get_text_id(text_id_arg):
    """Get or create text_id"""
    if text_id_arg:
        return text_id_arg
    
    # Create from input file
    config = PipelineConfig()
    api_client = APIClient(config)
    text_manager = TextManager(api_client)
    
    text_id = await text_manager.get_or_create_text()
    if not text_id:
        logger.error("Failed to get text_id")
        return None
    
    return text_id

async def main():
    args = parse_arguments()
    setup_signal_handlers()
    
    print("🎤 Track 1 Speech Pipeline")
    print("=========================")
    
    # Sync ngrok URL at startup
    print("🔗 Syncing ngrok URL...")
    success, ngrok_url = sync_ngrok_url()
    if success and ngrok_url:
        print(f"✅ Using ngrok URL: {ngrok_url}")
    else:
        print("⚠️  Could not sync ngrok URL, using localhost")
    
    try:
        # Get text_id
        text_id = await get_text_id(args.text_id)
        if not text_id:
            sys.exit(1)
        
        logger.info(f"Starting speech pipeline for text {text_id}")
        
        # Run the pipeline service
        success = await run_speech_pipeline(text_id, ensure_server=True)
        
        if success:
            logger.info("✅ Speech pipeline completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Speech pipeline failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 