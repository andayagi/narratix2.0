from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    ANTHROPIC_API_KEY: str = ""
    HUME_API_KEY: str = ""
    
    # Database
    DATABASE_URL: str = "sqlite:///./narratix.db"
    
    class Config:
        env_file = ".env" 