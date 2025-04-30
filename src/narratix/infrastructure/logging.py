import logging
import logging.handlers
import os
from pathlib import Path

LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_FILE = LOG_DIR / "narratix.log"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Define log format
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
formatter = logging.Formatter(log_format)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG) # Set root logger level

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) # Console logs INFO and above
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

# File Handler (Rotating)
# Rotate logs every 10MB, keep 5 backup logs
file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG) # File logs DEBUG and above
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

# Get logger for the application
def get_logger(name: str) -> logging.Logger:
    """Gets a configured logger instance."""
    return logging.getLogger(name)

# Example Usage (can be removed later)
if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")
    print(f"Logging configured. Check console and {LOG_FILE}") 