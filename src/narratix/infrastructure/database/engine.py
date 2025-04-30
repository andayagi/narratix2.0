"""Database engine module."""

from typing import Optional
import threading

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import DeclarativeBase

from .config import DB_CONFIG, IS_SQLITE

# Thread-local storage for the engine
_ENGINE_LOCAL = threading.local()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_engine() -> Engine:
    """
    Get or create a SQLAlchemy database engine for the current thread.
    
    Returns:
        Engine: SQLAlchemy engine instance.
    """
    # Check if engine already exists in thread-local storage
    if not hasattr(_ENGINE_LOCAL, "engine"):
        # Create engine with configuration from environment variables
        connect_args = {}
        
        # Special handling for SQLite
        if IS_SQLITE:
            # Enable foreign key constraints for SQLite
            connect_args["check_same_thread"] = False
        
        _ENGINE_LOCAL.engine = create_engine(
            DB_CONFIG["sqlalchemy.url"],
            echo=DB_CONFIG["sqlalchemy.echo"],
            pool_size=DB_CONFIG["sqlalchemy.pool_size"],
            pool_timeout=DB_CONFIG["sqlalchemy.pool_timeout"],
            pool_recycle=DB_CONFIG["sqlalchemy.pool_recycle"],
            max_overflow=DB_CONFIG["sqlalchemy.max_overflow"],
            connect_args=connect_args,
        )
    
    return _ENGINE_LOCAL.engine


def create_tables() -> None:
    """Create all tables defined in the models."""
    engine = get_engine()
    Base.metadata.create_all(engine) 