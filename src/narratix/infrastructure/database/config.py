"""Database configuration module."""

import os
from typing import Dict, Any

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default SQLite database for development
DEFAULT_SQLITE_URL = "sqlite:///narratix.db"

# Database configuration with environment variables
DB_CONFIG: Dict[str, Any] = {
    "sqlalchemy.url": os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL),
    "sqlalchemy.echo": os.getenv("DATABASE_ECHO", "false").lower() == "true",
    "sqlalchemy.pool_size": int(os.getenv("DATABASE_POOL_SIZE", "5")),
    "sqlalchemy.pool_timeout": int(os.getenv("DATABASE_POOL_TIMEOUT", "30")),
    "sqlalchemy.pool_recycle": int(os.getenv("DATABASE_POOL_RECYCLE", "1800")),
    "sqlalchemy.max_overflow": int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
}

# Determine if we're using SQLite (important for some SQLAlchemy settings)
IS_SQLITE = DB_CONFIG["sqlalchemy.url"].startswith("sqlite") 