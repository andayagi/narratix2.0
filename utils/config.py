"""Configuration utilities for Narratix."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Import our new logging module
from narratix.utils.logging import get_logger, SessionLogger

# Load environment variables from .env file
load_dotenv()

# Initialize module logger
logger = get_logger(__name__)

# API Configurations
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
HUME_API_KEY = os.getenv("HUME_API_KEY", "")

# Project Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(exist_ok=True)

def setup_run_logging(run_type: str, run_id: str = None) -> str:
    """
    Set up logging for a specific run.
    
    Args:
        run_type: Type of run (e.g., 'text_analysis', 'voice_generation')
        run_id: Optional identifier for the run
        
    Returns:
        Session ID for the run
    """
    # Create a session name that includes the run type
    session_name = f"{run_type}_{run_id}" if run_id else run_type
    session_id = SessionLogger.start_session(session_name)
    
    # Log basic run information
    run_logger = get_logger(f"narratix.{run_type}", {
        "run_type": run_type,
        "run_id": run_id
    })
    run_logger.info(f"Starting {run_type} run" + (f" (ID: {run_id})" if run_id else ""))
    
    return session_id

def validate_config() -> bool:
    """Validate that required configuration is available."""
    config_logger = get_logger(__name__, {"operation": "config_validation"})
    
    if not ANTHROPIC_API_KEY:
        config_logger.warning("ANTHROPIC_API_KEY not found in environment variables")
        return False
    
    if not HUME_API_KEY:
        config_logger.warning("HUME_API_KEY not found in environment variables")
        return False
    
    config_logger.info("Configuration validation successful")
    return True