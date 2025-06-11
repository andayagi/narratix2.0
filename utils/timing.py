import time
import asyncio
from functools import wraps
from utils.logging import get_logger

def time_it(service_name: str):
    """
    A decorator to log the execution time of a function.
    Works with both sync and async functions.
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                logger = get_logger(service_name)
                start_time = time.time()
                logger.info(f"Starting service: {service_name}")
                
                result = await func(*args, **kwargs)
                
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"Finished service: {service_name}. Duration: {duration:.2f} seconds")
                
                return result
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                logger = get_logger(service_name)
                start_time = time.time()
                logger.info(f"Starting service: {service_name}")
                
                result = func(*args, **kwargs)
                
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"Finished service: {service_name}. Duration: {duration:.2f} seconds")
                
                return result
            return sync_wrapper
    return decorator 