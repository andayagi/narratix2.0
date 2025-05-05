"""
Centralized logging configuration for Narratix.

This module provides a unified logging system for the entire application,
with structured JSON logs, session-based organization, and contextual logging.
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Configure base logging directory
LOGS_DIR = Path("logs")

class JsonFormatter(logging.Formatter):
    """Formatter that outputs JSON strings after formatting the log record."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a record as JSON."""
        # Start with the basic log record attributes
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        # Add location information for debugging
        if record.levelno <= logging.DEBUG:
            log_entry["location"] = f"{record.pathname}:{record.lineno}"
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add any context data attached to the record
        if hasattr(record, 'context') and record.context:
            log_entry.update(record.context)
            
        return json.dumps(log_entry)

class ContextAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context to log records."""
    
    def process(self, msg, kwargs):
        """Process the logging message and keyword arguments."""
        # Ensure we have an extra dict with a context key
        kwargs.setdefault('extra', {}).setdefault('context', {})
        
        # Update the context with our values
        if self.extra:
            kwargs['extra']['context'].update(self.extra)
            
        return msg, kwargs

class SessionLogger:
    """
    Manages logging for a session or run of the application.
    
    A session is a logical unit of execution, such as a specific test run,
    text analysis, or voice generation operation.
    """
    
    _current_session: Optional[str] = None
    _session_log_file: Optional[str] = None
    _console_handler_configured: bool = False # Renamed for clarity
    
    @classmethod
    def start_session(cls, session_name: Optional[str] = None) -> str:
        """
        Start a new logging session. Ensures only one file handler is active.
        Logs are saved in logs/YYYYMMDD/session_id.log
        
        Args:
            session_name: Optional name for the session. If not provided,
                          a timestamp-based name will be generated.
                          
        Returns:
            The session ID.
        """
        # Generate session ID and timestamp components
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        date_str = now.strftime("%Y%m%d")
        session_id = session_name or f"session_{timestamp}"
        
        # Create date-based log directory
        date_dir = LOGS_DIR / date_str
        date_dir.mkdir(parents=True, exist_ok=True) # Ensure the date directory exists
        
        # Define log file path within the date directory
        log_file_name = f"{session_id}.log" # Keep filename simpler
        log_file = date_dir / log_file_name
        
        # Set up log file path for the session
        cls._session_log_file = str(log_file)
        cls._current_session = session_id
        
        # Configure the root logger handlers for this session
        cls._configure_root_logger(log_file)
        
        # Log session start
        logging.info(f"Started logging session: {session_id} -> {log_file.relative_to(LOGS_DIR)}", 
                     extra={"context": {"session_id": session_id}})
        
        return session_id
    
    @classmethod
    def _configure_root_logger(cls, log_file: Path):
        """Configure the root logger handlers for the current session."""
        root_logger = logging.getLogger()
        # Set level every time in case it was changed elsewhere
        root_logger.setLevel(logging.INFO) 
        
        # Remove existing file handlers first
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                # Close the handler before removing to release the file lock
                handler.close() 
                root_logger.removeHandler(handler)
        
        # Add console handler only if not already added
        if not cls._console_handler_configured:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(JsonFormatter())
            root_logger.addHandler(console_handler)
            cls._console_handler_configured = True

        # Add the file handler for the new session
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JsonFormatter())
        root_logger.addHandler(file_handler)

    @classmethod
    def get_logger(cls, name: str, context: Dict[str, Any] = None) -> logging.LoggerAdapter:
        """
        Get a logger with session context.
        
        Args:
            name: Logger name (typically __name__)
            context: Additional context data to include in all log records
            
        Returns:
            A logger adapter with context
        """
        # Start a default session if none exists
        if not cls._current_session:
            # Pass a default name or let it generate timestamp based
            cls.start_session("default_session") 
        
        # Add session ID to context
        context_data = context or {}
        context_data["session_id"] = cls._current_session
        
        # Get the logger and wrap with context adapter
        logger = logging.getLogger(name)
        # Make sure logger propagates to root logger where handlers are set
        logger.propagate = True 
        return ContextAdapter(logger, context_data)
    
    @classmethod
    def get_session_log_file(cls) -> Optional[str]:
        """Get the path to the current session log file."""
        return cls._session_log_file
    
    @classmethod
    def get_current_session(cls) -> Optional[str]:
        """Get the current session ID."""
        return cls._current_session

# Initialize logs directory
LOGS_DIR.mkdir(exist_ok=True)

# Convenience function to get a logger with context
def get_logger(name: str, context: Dict[str, Any] = None) -> logging.LoggerAdapter:
    """
    Get a logger with session context.
    
    Args:
        name: Logger name (typically __name__)
        context: Additional context data to include in all log records
        
    Returns:
        A logger adapter with context
    """
    return SessionLogger.get_logger(name, context)