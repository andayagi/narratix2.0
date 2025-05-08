"""
HTTP client patching utility to enable automatic logging for all httpx requests.

This module monkey patches httpx to use our logging transport by default.
Import this module early in the application startup to ensure all HTTP calls are logged.
"""

import httpx
import logging
import json
from typing import Dict, Any, Optional
from utils.logging import get_logger

# Initialize API logger
api_logger = get_logger("api.http.client", is_api=True)

# Store original transport classes for reference
original_http_transport = httpx.HTTPTransport
original_async_transport = httpx.AsyncHTTPTransport

# Store original handle_request methods
original_handle_request = original_http_transport.handle_request
original_handle_async_request = original_async_transport.handle_async_request

def is_audio_content(headers: Dict) -> bool:
    """Check if the content is audio based on headers."""
    content_type = headers.get('content-type', '').lower()
    return any(media_type in content_type for media_type in [
        'audio/', 'voice/', 'mp3', 'wav', 'ogg', 'mpeg'
    ])

def extract_request_body(request) -> Optional[Any]:
    """Extract and potentially parse the request body."""
    if not request.content:
        return None
    
    try:
        # Check content type to determine how to handle the body
        content_type = request.headers.get('content-type', '').lower()
        
        # Skip extracting body for audio content
        if is_audio_content(request.headers):
            return "[AUDIO CONTENT - NOT LOGGED]"
            
        # Try to parse JSON
        if 'application/json' in content_type:
            # Convert bytes to string and parse as JSON
            return json.loads(request.content.decode('utf-8'))
        
        # For text content, just decode as string
        if 'text/' in content_type:
            return request.content.decode('utf-8')
            
        # For other types, provide a summary
        return f"[BINARY CONTENT - {len(request.content)} bytes]"
    except Exception as e:
        return f"[ERROR EXTRACTING BODY: {str(e)}]"

def extract_response_body(response) -> Optional[Any]:
    """Extract and potentially parse the response body."""
    try:
        # Check if the response has content
        if not hasattr(response, 'read') or not callable(getattr(response, 'read', None)):
            return None
            
        # Skip extracting body for audio content
        if is_audio_content(response.headers):
            return "[AUDIO CONTENT - NOT LOGGED]"
        
        # Check if this is a streaming response
        is_stream = getattr(response, 'is_stream', False) or getattr(response, 'stream', False)
        if is_stream:
            return "[STREAMING RESPONSE - CANNOT LOG BODY WITHOUT CONSUMING STREAM]"
        
        # Get the content type
        content_type = response.headers.get('content-type', '').lower()
        
        # Read the content (this might consume the response stream)
        content = response.read()
        
        # If no content, return None
        if not content:
            return None
        
        # Try to parse JSON
        if 'application/json' in content_type:
            return json.loads(content.decode('utf-8'))
        
        # For text content, just decode as string
        if 'text/' in content_type:
            return content.decode('utf-8')
            
        # For other types, provide a summary
        return f"[BINARY CONTENT - {len(content)} bytes]"
    except Exception as e:
        return f"[ERROR EXTRACTING BODY: {str(e)}]"

def log_request(request):
    """Log the request details"""
    # Extract body content if available
    body = extract_request_body(request)
    
    # Create log entry with full HTTP request details
    logging.getLogger("api.http").info(
        f"HTTP Request: {request.method} {request.url}",
        extra={
            'http_request': {
                'method': request.method,
                'url': str(request.url),
                'headers': dict(request.headers),
                'body': body
            }
        }
    )

def log_response(response):
    """Log the response details"""
    try:
        # Extract headers
        headers = dict(response.headers) if hasattr(response, 'headers') else {}
        
        # Extract body content if available
        body = extract_response_body(response)
        
        # Create log entry with full HTTP response details
        logging.getLogger("api.http").info(
            f"HTTP Response: {response.status_code}",
            extra={
                'http_response': {
                    'status_code': response.status_code,
                    'headers': headers,
                    'body': body
                }
            }
        )
    except Exception as e:
        logging.getLogger("api.http").error(f"Error logging HTTP response: {e}")

# Define patched handle_request methods
def patched_handle_request(self, request):
    """Patched synchronous handle_request with logging"""
    log_request(request)
    response = original_handle_request(self, request)
    log_response(response)
    return response

async def patched_handle_async_request(self, request):
    """Patched asynchronous handle_request with logging"""
    log_request(request)
    response = await original_handle_async_request(self, request)
    log_response(response)
    return response

def patch_httpx():
    """
    Patch httpx to use our logging transport by default.
    This ensures all HTTP calls in the application are logged, even those made by third-party libraries.
    """
    # Patch the handle_request methods directly
    httpx.HTTPTransport.handle_request = patched_handle_request
    httpx.AsyncHTTPTransport.handle_async_request = patched_handle_async_request

def unpatch_httpx():
    """
    Restore the original httpx transport classes.
    This is mainly useful for testing.
    """
    # Restore the original handle_request methods
    httpx.HTTPTransport.handle_request = original_handle_request
    httpx.AsyncHTTPTransport.handle_async_request = original_handle_async_request 