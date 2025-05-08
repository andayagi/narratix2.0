"""Configuration utilities for Narratix."""

import os
from pathlib import Path
from dotenv import load_dotenv
from utils.logging import get_logger, SessionLogger
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union

# Load environment variables from .env file
load_dotenv()

# Initialize module logger
logger = get_logger(__name__)

# Project Paths
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = PROJECT_ROOT / "logs"
AUDIO_DIR = PROJECT_ROOT / "audio"

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(exist_ok=True)
# Create audio directory if it doesn't exist
AUDIO_DIR.mkdir(exist_ok=True)

# Add tracking for active sessions 
_active_run_sessions: Dict[str, str] = {}

# Settings class for compatibility
class Settings:
    """Settings container class for application configuration"""
    def __init__(self):
        # Read API keys directly from environment to ensure latest values
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        self.HUME_API_KEY = os.getenv("HUME_API_KEY", "")
        self.PROJECT_ROOT = PROJECT_ROOT
        self.OUTPUT_DIR = OUTPUT_DIR
        self.LOGS_DIR = LOGS_DIR
        self.AUDIO_STORAGE_PATH = os.getenv("AUDIO_STORAGE_PATH", str(AUDIO_DIR))

# Create a singleton settings instance
settings = Settings()

def setup_run_logging(run_type: str, run_id: str = None) -> str:
    """
    Set up logging for a specific run.
    
    Args:
        run_type: Type of run (e.g., 'text_analysis', 'voice_generation')
        run_id: Optional identifier for the run
        
    Returns:
        Session ID for the run
    """
    # Check if we already have an active session for this run_type
    if run_type in _active_run_sessions:
        session_id = _active_run_sessions[run_type]
        # Use existing session - no need to create a new one
        run_logger = get_logger(f"narratix.{run_type}", {
            "run_type": run_type,
            "run_id": run_id
        })
        run_logger.info(f"Reusing existing {run_type} run session (ID: {session_id})")
        return session_id
    
    # Create a session name that includes the run type
    session_name = f"{run_type}_{run_id}" if run_id else run_type
    session_id = SessionLogger.start_session(session_name)
    
    # Store session ID for future reuse
    _active_run_sessions[run_type] = session_id
    
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
    
    # Re-read from environment to ensure latest values
    if not os.getenv("ANTHROPIC_API_KEY"):
        config_logger.warning("ANTHROPIC_API_KEY not found in environment variables")
        return False
    
    if not os.getenv("HUME_API_KEY"):
        config_logger.warning("HUME_API_KEY not found in environment variables")
        return False
    
    config_logger.info("Configuration validation successful")
    return True