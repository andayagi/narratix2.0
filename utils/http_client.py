"""
Shared HTTP client utilities for optimized connection reuse across services.
Supports both synchronous and asynchronous operations for parallel processing.
"""

import httpx
import requests
from typing import Optional
import threading
from utils.logging import get_logger

logger = get_logger(__name__)

# Global HTTP clients with connection pooling
_sync_client: Optional[requests.Session] = None
_async_client: Optional[httpx.AsyncClient] = None
_client_lock = threading.Lock()

# HTTP client configuration
HTTP_TIMEOUT = 300  # 5 minutes for audio generation requests
CONNECTION_POOL_SIZE = 25  # Match database pool size
MAX_CONNECTIONS = 35      # Match database max overflow

def get_sync_client() -> requests.Session:
    """
    Get a shared synchronous HTTP client with connection pooling.
    Thread-safe singleton pattern.
    """
    global _sync_client
    
    if _sync_client is None:
        with _client_lock:
            if _sync_client is None:
                _sync_client = requests.Session()
                
                # Configure connection pooling
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=CONNECTION_POOL_SIZE,
                    pool_maxsize=MAX_CONNECTIONS,
                    max_retries=3
                )
                _sync_client.mount('http://', adapter)
                _sync_client.mount('https://', adapter)
                
                # Set timeout
                _sync_client.timeout = HTTP_TIMEOUT
                
                logger.info(f"Initialized shared sync HTTP client with {CONNECTION_POOL_SIZE} pool connections")
    
    return _sync_client

def get_async_client() -> httpx.AsyncClient:
    """
    Get a shared asynchronous HTTP client with connection pooling.
    Thread-safe singleton pattern.
    """
    global _async_client
    
    if _async_client is None:
        with _client_lock:
            if _async_client is None:
                limits = httpx.Limits(
                    max_keepalive_connections=CONNECTION_POOL_SIZE,
                    max_connections=MAX_CONNECTIONS
                )
                
                _async_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(HTTP_TIMEOUT),
                    limits=limits
                )
                
                logger.info(f"Initialized shared async HTTP client with {CONNECTION_POOL_SIZE} pool connections")
    
    return _async_client

async def close_async_client():
    """Close the shared async HTTP client."""
    global _async_client
    
    if _async_client is not None:
        with _client_lock:
            if _async_client is not None:
                await _async_client.aclose()
                _async_client = None
                logger.info("Closed shared async HTTP client")

def close_sync_client():
    """Close the shared sync HTTP client."""
    global _sync_client
    
    if _sync_client is not None:
        with _client_lock:
            if _sync_client is not None:
                _sync_client.close()
                _sync_client = None
                logger.info("Closed shared sync HTTP client")

def cleanup_clients():
    """Close all shared HTTP clients. Call this on application shutdown."""
    close_sync_client()
    # Note: async client requires await, so it should be closed separately in async context

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