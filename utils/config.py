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

@dataclass
class ReplicateAudioSettings:
    """Configuration settings for Replicate audio generation services."""
    
    # Webhook timeout settings
    webhook_timeout: int = 300  # 5 minutes - default webhook completion timeout
    sound_effects_timeout: int = 300  # 5 minutes - sound effects completion timeout
    
    # HTTP client settings
    download_timeout: int = 30  # 30 seconds - audio download timeout
    max_file_size: int = 50_000_000  # 50MB - maximum audio file size
    
    # FFmpeg processing settings
    ffmpeg_timeout: int = 30  # 30 seconds - ffmpeg command timeout
    
    # Audio processing settings
    silence_threshold: str = "-60dB"  # Silence detection threshold for trimming
    
    @classmethod
    def from_environment(cls) -> 'ReplicateAudioSettings':
        """Create settings from environment variables with fallback to defaults."""
        return cls(
            webhook_timeout=int(os.getenv("REPLICATE_WEBHOOK_TIMEOUT", "300")),
            sound_effects_timeout=int(os.getenv("REPLICATE_SOUND_EFFECTS_TIMEOUT", "300")),
            download_timeout=int(os.getenv("REPLICATE_DOWNLOAD_TIMEOUT", "30")),
            max_file_size=int(os.getenv("REPLICATE_MAX_FILE_SIZE", "50000000")),
            ffmpeg_timeout=int(os.getenv("REPLICATE_FFMPEG_TIMEOUT", "30")),
            silence_threshold=os.getenv("REPLICATE_SILENCE_THRESHOLD", "-60dB")
        )

# Settings class for compatibility
class Settings:
    """Settings container class for application configuration"""
    def __init__(self):
        # Read API keys directly from environment to ensure latest values
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        self.HUME_API_KEY = os.getenv("HUME_API_KEY", "")
        self.REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
        
        # Production Environment Configuration
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.BASE_URL = self._get_base_url()
        
        # CORS Configuration
        self.CORS_ORIGINS = self._get_cors_origins()
        
        # Webhook Monitoring Configuration
        self.WEBHOOK_MONITORING_ENABLED = os.getenv("WEBHOOK_MONITORING_ENABLED", "true").lower() == "true"
        self.WEBHOOK_FAILURE_ALERT_THRESHOLD = int(os.getenv("WEBHOOK_FAILURE_ALERT_THRESHOLD", "5"))
        self.WEBHOOK_TIMEOUT_SECONDS = int(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "30"))
        
        self.PROJECT_ROOT = PROJECT_ROOT
        self.OUTPUT_DIR = OUTPUT_DIR
        self.LOGS_DIR = LOGS_DIR
        self.AUDIO_STORAGE_PATH = os.getenv("AUDIO_STORAGE_PATH", str(AUDIO_DIR))
        
        # WhisperX/Force Alignment Configuration
        self.WHISPERX_MODEL_SIZE = os.getenv("WHISPERX_MODEL_SIZE", "base")
        self.WHISPERX_COMPUTE_TYPE = os.getenv("WHISPERX_COMPUTE_TYPE", "float32")
        self.SOUND_EFFECTS_VOLUME_LEVEL = float(os.getenv("SOUND_EFFECTS_VOLUME_LEVEL", "0.3"))
        
        # Replicate Audio Configuration
        self.replicate_audio = ReplicateAudioSettings.from_environment()
    
    def _get_base_url(self) -> str:
        """Get BASE_URL with proper HTTPS validation for production."""
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        
        # Ensure HTTPS in production
        if self.ENVIRONMENT == "production":
            if not base_url.startswith("https://"):
                logger.warning(f"Production BASE_URL should use HTTPS: {base_url}")
                # Auto-correct http to https in production
                if base_url.startswith("http://"):
                    base_url = base_url.replace("http://", "https://", 1)
                    logger.info(f"Auto-corrected BASE_URL to HTTPS: {base_url}")
                elif not base_url.startswith("https://"):
                    base_url = f"https://{base_url}"
                    logger.info(f"Added HTTPS prefix to BASE_URL: {base_url}")
        
        return base_url
    
    def _get_cors_origins(self) -> List[str]:
        """Get CORS origins based on environment."""
        if self.ENVIRONMENT == "production":
            # Restrict CORS origins in production
            origins_str = os.getenv("CORS_ORIGINS", "")
            if origins_str:
                origins = [origin.strip() for origin in origins_str.split(",")]
                logger.info(f"Production CORS origins: {origins}")
                return origins
            else:
                logger.warning("No CORS_ORIGINS specified for production environment")
                return []
        else:
            # Allow all origins in development
            return ["*"]
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"
    
    def get_webhook_url(self, content_type: str, content_id: int) -> str:
        """Construct webhook URL with proper validation and ngrok sync for development."""
        # For development, ensure ngrok URL is current
        if not self.is_production():
            try:
                # Import here to avoid circular imports
                from utils.ngrok_sync import sync_ngrok_url
                success, ngrok_url = sync_ngrok_url(silent=True)
                if success and ngrok_url:
                    current_base_url = ngrok_url
                else:
                    # Fallback to environment variable
                    current_base_url = os.getenv("BASE_URL", "http://localhost:8000")
            except ImportError:
                # Fallback if ngrok_sync not available
                current_base_url = os.getenv("BASE_URL", "http://localhost:8000")
        else:
            # In production, read from environment
            current_base_url = os.getenv("BASE_URL", "http://localhost:8000")
            
            # Apply production HTTPS validation
            if not current_base_url.startswith("https://"):
                if current_base_url.startswith("http://"):
                    current_base_url = current_base_url.replace("http://", "https://", 1)
                elif not current_base_url.startswith("https://"):
                    current_base_url = f"https://{current_base_url}"
        
        url = f"{current_base_url}/api/replicate-webhook/{content_type}/{content_id}"
        
        # Validate HTTPS in production
        if self.is_production() and not url.startswith("https://"):
            logger.error(f"Webhook URL must use HTTPS in production: {url}")
            raise ValueError(f"Webhook URL must use HTTPS in production: {url}")
        
        return url

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
    
    if not os.getenv("REPLICATE_API_TOKEN"):
        config_logger.warning("REPLICATE_API_TOKEN not found in environment variables")
        return False
    
    config_logger.info("Configuration validation successful")
    return True