from pydantic import BaseSettings
from typing import Optional, Dict, Any
from pathlib import Path

class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""
    
    # API Keys
    anthropic_api_key: str
    hume_api_key: str
    
    # Database
    database_url: str = "sqlite:///data/narratix.db"
    
    # Paths
    output_dir: Path = Path("output")
    logs_dir: Path = Path("logs")
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Logging
    log_level: str = "INFO"
    structured_logging: bool = True
    
    # Cache Settings
    cache_ttl_seconds: int = 3600
    
    # Voice Management
    max_voices_per_story: int = 30
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8" 