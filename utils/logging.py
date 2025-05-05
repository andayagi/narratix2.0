import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

from .config import settings

# Configure basic logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("narratix")

class APILogger:
    @staticmethod
    def log_api_request(
        operation: str,
        request_data: Dict[str, Any],
        text_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log API request and return log entry"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "text_id": text_id,
            "request": request_data
        }
        
        logger.info(f"API Request - {operation}: {json.dumps(request_data)}")
        
        return log_entry
    
    @staticmethod
    def log_api_response(
        log_entry: Dict[str, Any],
        response_data: Dict[str, Any],
        status: str
    ) -> Dict[str, Any]:
        """Log API response and update log entry"""
        log_entry["response"] = response_data
        log_entry["status"] = status
        
        logger.info(f"API Response - {log_entry['operation']} - {status}: {json.dumps(response_data)}")
        
        # Also save to a timestamped JSON file for detailed logging
        log_dir = os.path.join("logs", "api_calls")
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"{log_entry['operation']}_{timestamp}.json")
        
        with open(log_file, "w") as f:
            json.dump(log_entry, f, indent=2)
        
        return log_entry