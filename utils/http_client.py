import httpx
import json
from typing import Dict, Any, Optional, Union, List, Callable
from utils.logging import get_logger, SessionLogger
from utils.http_patch import patch_httpx

# Initialize HTTP patching to enable request logging for all clients
patch_httpx()

def create_client(timeout: float = 60.0, **kwargs) -> httpx.Client:
    """
    Create a synchronous HTTP client.
    
    Args:
        timeout: Request timeout in seconds
        **kwargs: Additional arguments to pass to httpx.Client
        
    Returns:
        An httpx.Client
    """
    return httpx.Client(timeout=timeout, **kwargs)

def create_async_client(timeout: float = 60.0, **kwargs) -> httpx.AsyncClient:
    """
    Create an asynchronous HTTP client.
    
    Args:
        timeout: Request timeout in seconds
        **kwargs: Additional arguments to pass to httpx.AsyncClient
        
    Returns:
        An httpx.AsyncClient
    """
    return httpx.AsyncClient(timeout=timeout, **kwargs)

def test_api_logging():
    """
    Test function to verify API logging is working correctly.
    This makes a simple HTTP request and ensures it's logged properly.
    """
    # Ensure we have an active session
    session_id = SessionLogger.get_current_session()
    if not session_id:
        session_id = SessionLogger.start_session("api_logging_test")
    
    # Create a client
    client = create_client()
    
    # Make a test request to a public API
    try:
        response = client.get("https://httpbin.org/get")
        print(f"Test request successful: {response.status_code}")
        print(f"API logs should be in: {SessionLogger.get_session_api_log_file()}")
        return True
    except Exception as e:
        print(f"Test request failed: {e}")
        return False 