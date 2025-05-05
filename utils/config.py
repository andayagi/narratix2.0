import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    # API Keys
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    HUME_API_KEY: str = os.getenv("HUME_API_KEY", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Paths
    AUDIO_STORAGE_PATH: str = os.getenv("AUDIO_STORAGE_PATH", "audio_files")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/narratix.log")
    
    class Config:
        env_file = ".env"

settings = Settings()

# Create directories if they don't exist
os.makedirs(settings.AUDIO_STORAGE_PATH, exist_ok=True)
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)