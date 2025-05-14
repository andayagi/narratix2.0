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
import inspect
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Literal

# Configure base logging directory - make absolute to ensure consistency
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
LOGS_DIR = PROJECT_ROOT / "logs"

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
            
        # Add HTTP request/response info if present
        if hasattr(record, 'http_request'):
            log_entry["http_request"] = {
                "method": record.http_request.get("method"),
                "url": record.http_request.get("url"),
                "headers": record.http_request.get("headers", {}),
                "body": record.http_request.get("body")
            }
            
        if hasattr(record, 'http_response'):
            log_entry["http_response"] = {
                "status_code": record.http_response.get("status_code"),
                "headers": record.http_response.get("headers", {}),
                "body": record.http_response.get("body")
            }
        
        # Add any context data attached to the record
        if hasattr(record, 'context') and record.context:
            log_entry.update(record.context)
            
        return json.dumps(log_entry)

class HumanReadableFormatter(logging.Formatter):
    """Formatter that outputs human-readable log messages."""
    
    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)
        self.default_fmt = '[%(asctime)s] %(levelname)s - %(name)s: %(message)s'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a record in human-readable format."""
        # Use a basic format for the main log line
        self._style._fmt = self.default_fmt
        formatted = super().format(record)
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\nException: {self.formatException(record.exc_info)}"
        
        # Add HTTP request info if present
        if hasattr(record, 'http_request'):
            req = record.http_request
            formatted += f"\nRequest: {req.get('method')} {req.get('url')}"
            if req.get('headers'):
                formatted += "\nRequest Headers:"
                for k, v in req.get('headers', {}).items():
                    if k.lower() in ['authorization', 'x-api-key', 'api-key']:
                        v = '[REDACTED]'
                    formatted += f"\n  {k}: {v}"
                    
            if 'body' in req and req['body']:
                formatted += "\nRequest Body:"
                formatted += self._format_body(req['body'])
        
        # Add HTTP response info if present
        if hasattr(record, 'http_response'):
            resp = record.http_response
            formatted += f"\nResponse Status: {resp.get('status_code')}"
            if resp.get('headers'):
                formatted += "\nResponse Headers:"
                for k, v in resp.get('headers', {}).items():
                    formatted += f"\n  {k}: {v}"
                    
            if 'body' in resp and resp['body']:
                formatted += "\nResponse Body:"
                formatted += self._format_body(resp['body'])
        
        # Add context data if present (selectively)
        if hasattr(record, 'context') and record.context:
            # Only show important context keys to avoid clutter
            #important_keys = ['session_id', 'user_id', 'operation', 'request_id']
            #context_items = []
            #for key in important_keys:
            #    if key in record.context:
            #        context_items.append(f"{key}={record.context[key]}")
            
            #if context_items:
            #    formatted += f"\nContext: {', '.join(context_items)}"
            pass  # Add a pass statement to properly handle the empty if block
                
        return formatted
    
    def _format_body(self, body) -> str:
        """Format the body content in a readable way."""
        # Handle different body types
        if isinstance(body, (dict, list)):
            try:
                # Pretty print JSON with indentation
                return '\n' + self._pretty_print_json(body)
            except (TypeError, ValueError):
                pass
                
        # For non-JSON or if pretty printing fails
        body_str = str(body)
        if len(body_str) > 1000:
            # For very long strings, truncate with summary
            return f"\n  (truncated {len(body_str)} chars) {body_str[:1000]}..."
        else:
            # Indent each line to make it more readable
            return '\n  ' + body_str.replace('\n', '\n  ')
    
    def _pretty_print_json(self, data, max_depth=3, current_depth=0, indent_size=2):
        """
        Pretty print JSON with controlled depth to avoid too much output.
        For nested objects beyond max_depth, shows a summary instead.
        """
        if current_depth >= max_depth:
            # Summarize deeply nested objects
            if isinstance(data, dict):
                return f"{{... {len(data)} keys ...}}"
            elif isinstance(data, list):
                return f"[... {len(data)} items ...]"
            else:
                return str(data)
                
        if isinstance(data, dict):
            if not data:
                return "{}"
                
            result = "{"
            indent = " " * indent_size * (current_depth + 1)
            items = []
            
            for i, (key, value) in enumerate(data.items()):
                # Limit number of items for large dictionaries
                if i >= 10 and len(data) > 15:
                    items.append(f"\n{indent}... {len(data) - i} more items ...")
                    break
                    
                value_str = self._pretty_print_json(value, max_depth, current_depth + 1, indent_size)
                items.append(f"\n{indent}\"{key}\": {value_str}")
                
            result += ", ".join(items)
            result += f"\n{' ' * indent_size * current_depth}}}"
            return result
            
        elif isinstance(data, list):
            if not data:
                return "[]"
                
            result = "["
            indent = " " * indent_size * (current_depth + 1)
            items = []
            
            for i, value in enumerate(data):
                # Limit number of items for large lists
                if i >= 5 and len(data) > 10:
                    items.append(f"\n{indent}... {len(data) - i} more items ...")
                    break
                    
                value_str = self._pretty_print_json(value, max_depth, current_depth + 1, indent_size)
                items.append(f"\n{indent}{value_str}")
                
            result += ", ".join(items)
            result += f"\n{' ' * indent_size * current_depth}]"
            return result
            
        elif isinstance(data, str):
            # For strings, handle escaping and wrapping in quotes
            if len(data) > 100:
                return f"\"{data[:100]}...\""
            return f"\"{data}\""
            
        elif isinstance(data, bool):
            return "true" if data else "false"
            
        elif data is None:
            return "null"
            
        else:
            # Just convert numbers and other primitives to string
            return str(data)

class SimpleConsoleFormatter(logging.Formatter):
    """Simplified formatter for console output - doesn't show full request/response bodies."""
    
    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)
        self.default_fmt = '[%(asctime)s] %(levelname)s - %(name)s: %(message)s'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a record with simplified output for the console."""
        # Use a basic format for the main log line
        self._style._fmt = self.default_fmt
        formatted = super().format(record)
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\nException: {self.formatException(record.exc_info)}"
        
        # Skip HTTP request/response details completely for console output
        # This ensures we have the most minimal console logs
        
        return formatted

class ConsoleFilter(logging.Filter):
    """Filter to exclude detailed HTTP request/response logs from console output."""
    
    def filter(self, record):
        """Return False to block detailed HTTP logs from console."""
        # Allow non-HTTP logs through
        if not hasattr(record, 'http_request') and not hasattr(record, 'http_response'):
            return True
            
        # Block logs that have explicit HTTP request/response details
        if 'HTTP Request:' in record.getMessage() or 'HTTP Response:' in record.getMessage():
            return False
            
        # Allow other logs through
        return True

class APIFileHandler(logging.FileHandler):
    """File handler for detailed API logs that filters to only include API-related logs."""
    
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)
    
    def emit(self, record):
        """Only emit records with HTTP request/response data or API-related information."""
        # Check for HTTP request/response data
        if hasattr(record, 'http_request') or hasattr(record, 'http_response'):
            super().emit(record)
        # Also include logs from API-related loggers
        elif record.name.startswith('api.') or 'hume' in record.name.lower() or 'anthropic' in record.name.lower():
            super().emit(record)
        # Include logs with API-related messages
        elif any(term in record.getMessage().lower() for term in ['api', 'http', 'request', 'response']):
            super().emit(record)

class ContextualLogger(logging.LoggerAdapter):
    """Base logger adapter that adds context to log records."""
    
    def process(self, msg, kwargs):
        """Process the logging message and keyword arguments."""
        # Ensure we have an extra dict with a context key
        kwargs.setdefault('extra', {}).setdefault('context', {})
        
        # Update the context with our values
        if self.extra:
            kwargs['extra']['context'].update(self.extra)
            
        return msg, kwargs

class APILogger(ContextualLogger):
    """Logger adapter specifically for API calls with request/response tracking."""
    
    def log_request(self, method: str, url: str, headers: Dict = None, body: Any = None):
        """Log an API request."""
        self.info(f"HTTP Request: {method} {url}", extra={
            'http_request': {
                'method': method,
                'url': url,
                'headers': self._sanitize_headers(headers or {}),
                'body': body
            }
        })
    
    def log_response(self, status_code: int, headers: Dict = None, body: Any = None):
        """Log an API response."""
        self.info(f"HTTP Response: status_code={status_code}", extra={
            'http_response': {
                'status_code': status_code,
                'headers': headers or {},
                'body': body
            }
        })
    
    def _sanitize_headers(self, headers: Dict) -> Dict:
        """Remove sensitive information from headers."""
        sanitized = headers.copy()
        sensitive_keys = ['authorization', 'x-api-key', 'api-key']
        for key in headers:
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
        return sanitized

class SessionLogger:
    """
    Manages logging for a session or run of the application.
    
    A session is a logical unit of execution, such as a specific test run,
    text analysis, or voice generation operation.
    """
    
    _current_session: Optional[str] = None
    _session_log_file: Optional[str] = None
    _console_handler_configured: bool = False
    
    @classmethod
    def start_session(cls, session_name: Optional[str] = None) -> str:
        """
        Start a new logging session. Ensures only one file handler is active.
        Logs are saved in logs/YYYYMMDD/script_name_[timestamp].log
        
        Args:
            session_name: Name for the session, typically the script or test name.
                          If not provided, will try to auto-detect the calling script.
                          
        Returns:
            The session ID (which is now the log file name without .log).
        """
        # Generate session ID and timestamp components
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        date_str = now.strftime("%Y%m%d")
        
        # Auto-detect script name if session_name not provided
        if not session_name:
            # Try to get the name of the script that initiated this call
            try:
                # First, check if running under pytest by checking if 'pytest' is in sys.modules
                if 'pytest' in sys.modules:
                    # Try to detect pytest test file by checking stack frames
                    test_file = None
                    for frame_info in inspect.stack():
                        module = inspect.getmodule(frame_info[0])
                        if module and module.__file__:
                            file_path = Path(module.__file__)
                            # Look for test files in the stack
                            if file_path.name.startswith('test_') and not 'site-packages' in str(file_path):
                                test_file = file_path.stem
                                break
                    
                    if test_file:
                        session_name = test_file
                    else:
                        # If no test file found, check for PYTEST_CURRENT_TEST env var
                        pytest_current_test = os.environ.get('PYTEST_CURRENT_TEST', '')
                        if pytest_current_test:
                            # Extract the test file name from the env var
                            # Format is typically: tests/test_file.py::test_function
                            parts = pytest_current_test.split('::')[0].split('/')
                            if parts:
                                session_name = Path(parts[-1]).stem
                
                # Standard detection if not pytest or pytest detection failed
                if not session_name:
                    # Look deeper in the stack for a non-internal module
                    for i in range(1, 10):  # Check up to 10 frames
                        try:
                            frame = inspect.stack()[i]
                            module = inspect.getmodule(frame[0])
                            if module and module.__file__:
                                file_path = Path(module.__file__)
                                # Skip internal modules
                                if 'site-packages' not in str(file_path) and not file_path.name.startswith('_'):
                                    session_name = file_path.stem
                                    break
                        except (IndexError, AttributeError):
                            break
            except Exception as e:
                print(f"Error detecting script name: {e}")
                session_name = "unknown_script"
            
            # If still no session_name, use default
            if not session_name:
                session_name = "unknown_script"
        
        # Create the log file name in the format: session_name_[timestamp].log
        log_file_name = f"{session_name}_{timestamp}.log"
        session_id = f"{session_name}_{timestamp}"
        
        # Create date-based log directory with absolute path
        date_dir = LOGS_DIR / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Define log file path within the date directory
        log_file = date_dir / log_file_name
        
        # Set up log file path for the session
        cls._session_log_file = str(log_file)
        cls._current_session = session_id
        
        # Configure the root logger handlers for this session
        cls._configure_root_logger(log_file)
        
        # Log session start with absolute path for clarity
        logging.info(f"Started logging session: {session_id} -> {log_file}",
                     extra={"context": {"session_id": session_id}})
        
        return session_id
    
    @classmethod
    def _configure_root_logger(cls, log_file: Path):
        """Configure the root logger handlers for the current session."""
        root_logger = logging.getLogger()
        # Set level every time in case it was changed elsewhere
        root_logger.setLevel(logging.INFO)
        
        # Use JSON formatter for file logs
        file_formatter = JsonFormatter()
            
        # Always use the simplified formatter for console
        console_formatter = SimpleConsoleFormatter()
        
        # Remove existing file handlers first
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                # Close the handler before removing to release the file lock
                handler.close()
                root_logger.removeHandler(handler)
        
        # Remove existing console handlers if format has changed
        if cls._console_handler_configured:
            for handler in root_logger.handlers[:]:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    root_logger.removeHandler(handler)
            cls._console_handler_configured = False
            
        # Get console log level from environment variable, default to WARNING
        console_level_name = os.environ.get('LOG_LEVEL_CONSOLE', 'WARNING').upper()
        console_level = getattr(logging, console_level_name, logging.WARNING)
            
        # Add console handler with simplified formatter and configurable log level
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(console_level)  # Use configurable console level
        # Add filter to block detailed HTTP logs from console
        console_handler.addFilter(ConsoleFilter())
        root_logger.addHandler(console_handler)
        cls._console_handler_configured = True

        # Add the file handler for the new session with full details
        # Keep INFO level for file logs to capture all relevant information
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.INFO)  # Ensure we capture all INFO logs in files
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
            cls.start_session()  # Will auto-detect script name
        
        # Add session ID to context
        context_data = context or {}
        context_data["session_id"] = cls._current_session
        
        # Get the logger and wrap with context adapter
        logger = logging.getLogger(name)
        # Make sure logger propagates to root logger where handlers are set
        logger.propagate = True
        return ContextualLogger(logger, context_data)
    
    @classmethod
    def get_session_log_file(cls) -> Optional[str]:
        """Get the path to the current session log file."""
        return cls._session_log_file
    
    @classmethod
    def get_current_session(cls) -> Optional[str]:
        """Get the current session ID."""
        return cls._current_session

# Initialize logs directory
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Convenience function to get a logger with context
def get_logger(name: str, context: Dict[str, Any] = None) -> logging.LoggerAdapter:
    """
    Get a logger with session context.
    
    Args:
        name: Logger name (typically __name__)
        context: Additional context data to include in all log records
        
    Returns:
        A logger adapter with context that can handle API requests/responses
    """
    base_logger = SessionLogger.get_logger(name, context)
    # Always return an APILogger to ensure API requests/responses are properly logged
    return APILogger(base_logger.logger, base_logger.extra)