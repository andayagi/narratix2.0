#!/usr/bin/env python3
"""
CLI wrapper for Complete E2E Pipeline service.
Calls the service function directly without duplicating logic.

Usage:
    python3 scripts/simple_e2e_pipeline.py [text_id]
    
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

from services.complete_pipeline import run_complete_pipeline
from utils.logging import get_logger
from utils.ngrok_sync import smart_server_health_check

logger = get_logger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Run Complete E2E Pipeline (Text Analysis → Voice → Speech → Audio Analysis → Background Music || Sound Effects → Final Export)")
    parser.add_argument("text_id", type=int, nargs='?', help="Text ID to process (if not provided, creates from input file)")
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
    
    print("🎵 Simple E2E Pipeline")
    print("=====================")
    
    # Check server health upfront for webhook support
    print("🔗 Checking server health and webhook accessibility...")
    if not smart_server_health_check():
        print("❌ Server is not accessible - cannot receive webhooks")
        print("📋 Required setup:")
        print("   1. Start FastAPI server: uvicorn api.main:app --host 127.0.0.1 --port 8000")
        print("   2. Start ngrok tunnel: ngrok http 8000") 
        print("   3. Ensure BASE_URL environment variable is set to ngrok URL")
        sys.exit(1)
    
    print("✅ Server is accessible and ready for webhooks")
    
    try:
        text_id = args.text_id
        logger.info(f"Starting complete pipeline for text {text_id if text_id else 'from input file'}")
        
        # Run the pipeline service
        success = await run_complete_pipeline(text_id, ensure_server=True)
        
        if success:
            logger.info("✅ Complete pipeline completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Complete pipeline failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 