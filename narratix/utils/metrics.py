import time
from functools import wraps
import logging
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Simple in-memory metrics store
_metrics_store = {
    "counters": {},
    "timers": {},
    "gauges": {}
}

def increment_counter(name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
    """Increment a counter metric."""
    key = name
    if tags:
        key = f"{name}:{_tags_to_string(tags)}"
        
    if key not in _metrics_store["counters"]:
        _metrics_store["counters"][key] = 0
        
    _metrics_store["counters"][key] += value
    
def set_gauge(name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """Set a gauge metric value."""
    key = name
    if tags:
        key = f"{name}:{_tags_to_string(tags)}"
        
    _metrics_store["gauges"][key] = value

@contextmanager
def timer(name: str, tags: Optional[Dict[str, str]] = None):
    """Context manager for timing operations."""
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        key = name
        if tags:
            key = f"{name}:{_tags_to_string(tags)}"
            
        _metrics_store["timers"][key] = elapsed_time
        logger.debug(f"Operation {key} took {elapsed_time:.4f} seconds")

def timed(name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
    """Decorator for timing functions."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            metric_name = name or f"{func.__module__}.{func.__name__}"
            with timer(metric_name, tags):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def get_metrics() -> Dict[str, Any]:
    """Get all collected metrics."""
    return _metrics_store

def _tags_to_string(tags: Dict[str, str]) -> str:
    """Convert tags dictionary to string format."""
    return ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
