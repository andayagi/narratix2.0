"""
Utility for automatically syncing BASE_URL with current ngrok tunnel.

This module provides functions to automatically check and update the BASE_URL
when webhook-dependent scripts detect connectivity issues.
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Optional, Tuple
from utils.logging import get_logger

logger = get_logger(__name__)

def get_current_ngrok_url() -> Optional[str]:
    """
    Get the current ngrok tunnel URL from the ngrok API.
    
    Returns:
        Current HTTPS ngrok tunnel URL or None if not available
    """
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get("tunnels", [])
            
            # Look for HTTPS tunnel
            for tunnel in tunnels:
                if tunnel.get("proto") == "https":
                    return tunnel.get("public_url")
            
            logger.warning("No HTTPS tunnel found in ngrok")
            return None
        else:
            logger.warning(f"Failed to get ngrok tunnels (status: {response.status_code})")
            return None
            
    except requests.exceptions.ConnectionError:
        logger.debug("Cannot connect to ngrok API - ngrok may not be running")
        return None
    except Exception as e:
        logger.debug(f"Error getting ngrok URL: {e}")
        return None

def update_env_file(new_url: str) -> bool:
    """
    Update the BASE_URL in the .env file.
    
    Args:
        new_url: New BASE_URL to set
        
    Returns:
        True if successful, False otherwise
    """
    try:
        project_root = Path(__file__).parent.parent
        env_file = project_root / ".env"
        
        # Read existing .env content
        env_lines = []
        base_url_found = False
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add BASE_URL line
        updated_lines = []
        for line in env_lines:
            if line.strip().startswith("BASE_URL="):
                updated_lines.append(f"BASE_URL={new_url}\n")
                base_url_found = True
            else:
                updated_lines.append(line)
        
        # Add BASE_URL if not found
        if not base_url_found:
            updated_lines.append(f"BASE_URL={new_url}\n")
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            f.writelines(updated_lines)
        
        logger.info(f"Updated .env file with BASE_URL={new_url}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update .env file: {e}")
        return False

def sync_ngrok_url(silent: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Check and sync BASE_URL with current ngrok tunnel if needed.
    
    Args:
        silent: If True, suppress info messages (only log warnings/errors)
        
    Returns:
        Tuple of (success, new_url) where:
        - success: True if sync was successful or not needed
        - new_url: The current ngrok URL (whether updated or not)
    """
    current_env_url = os.getenv("BASE_URL")
    ngrok_url = get_current_ngrok_url()
    
    if not ngrok_url:
        if not silent:
            logger.warning("Could not get current ngrok URL - sync skipped")
        return False, None
    
    if current_env_url == ngrok_url:
        if not silent:
            logger.debug("BASE_URL is already synchronized with ngrok")
        return True, ngrok_url
    
    # URLs don't match - need to update
    if not silent:
        logger.info(f"Syncing BASE_URL: {current_env_url} -> {ngrok_url}")
    
    # Update environment variable for current session
    os.environ["BASE_URL"] = ngrok_url
    
    # Update .env file for persistence
    env_updated = update_env_file(ngrok_url)
    
    if env_updated:
        if not silent:
            logger.info("Successfully synced BASE_URL with current ngrok tunnel")
        return True, ngrok_url
    else:
        if not silent:
            logger.warning("Environment variable updated but .env file update failed")
        return False, ngrok_url

def auto_sync_on_connection_error(func):
    """
    Decorator that automatically syncs ngrok URL when connection errors occur.
    
    This decorator wraps functions that make HTTP requests and automatically
    tries to sync the ngrok URL if a connection error is detected.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.ConnectionError as e:
            logger.info("Connection error detected - attempting ngrok URL sync")
            success, new_url = sync_ngrok_url()
            
            if success and new_url:
                logger.info(f"Retrying with updated BASE_URL: {new_url}")
                # Retry the function once with updated URL
                try:
                    return func(*args, **kwargs)
                except Exception as retry_e:
                    logger.error(f"Retry failed after ngrok sync: {retry_e}")
                    raise
            else:
                logger.error("Failed to sync ngrok URL - cannot retry")
                raise
                
    return wrapper

def smart_server_health_check(base_url: str = None) -> bool:
    """
    Enhanced server health check that auto-syncs ngrok URL on failure.
    
    Args:
        base_url: Base URL to check (uses BASE_URL env var if not provided)
        
    Returns:
        True if server is healthy (after sync if needed), False otherwise
    """
    if base_url is None:
        base_url = os.getenv("BASE_URL")
    
    if not base_url:
        logger.error("No BASE_URL configured")
        return False
    
    # First attempt
    try:
        health_url = f"{base_url}/docs"
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            logger.debug(f"Server is healthy at {base_url}")
            return True
        else:
            logger.warning(f"Server responded with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        logger.info(f"Cannot connect to server at {base_url} - attempting ngrok sync")
    except requests.exceptions.Timeout:
        logger.warning(f"Server at {base_url} is not responding (timeout)")
        return False
    except Exception as e:
        logger.error(f"Error checking server health: {e}")
        return False
    
    # If we get here, there was a connection issue - try syncing
    logger.info("Attempting to sync ngrok URL and retry...")
    success, new_url = sync_ngrok_url(silent=True)
    
    if not success or not new_url:
        logger.error("Failed to sync ngrok URL")
        return False
    
    # Retry with new URL
    try:
        health_url = f"{new_url}/docs"
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            logger.info(f"Server is healthy after ngrok sync: {new_url}")
            return True
        else:
            logger.error(f"Server still not responding after sync (status: {response.status_code})")
            return False
            
    except Exception as e:
        logger.error(f"Server health check failed even after ngrok sync: {e}")
        return False 