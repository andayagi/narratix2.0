import logging
import sys
from pathlib import Path
import json
from datetime import datetime
from .config import settings

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logging():
    """Configure application logging."""
    # Create logs directory if it doesn't exist
    logs_dir = Path(settings.logs_dir)
    logs_dir.mkdir(exist_ok=True, parents=True)
    
    # Determine log file path
    log_file = logs_dir / f"narratix_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if settings.structured_logging:
        console_handler.setFormatter(JsonFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    if settings.structured_logging:
        file_handler.setFormatter(JsonFormatter())
    else:
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Set level for third-party libraries
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized. Log file: {log_file}")
    return root_logger
