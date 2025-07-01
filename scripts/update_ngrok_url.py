#!/usr/bin/env python3
"""
Auto-update BASE_URL with current ngrok tunnel URL

This script fetches the current ngrok tunnel URL and updates the BASE_URL
environment variable both in memory and in the .env file.

Usage:
    python3 scripts/update_ngrok_url.py
    python3 scripts/update_ngrok_url.py --check-only  # Just show current URLs
"""

import os
import sys
import json
import requests
import argparse
from pathlib import Path

def get_current_ngrok_url():
    """Get the current ngrok tunnel URL from the ngrok API."""
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get("tunnels", [])
            
            # Look for HTTPS tunnel
            for tunnel in tunnels:
                if tunnel.get("proto") == "https":
                    return tunnel.get("public_url")
            
            print("❌ No HTTPS tunnel found in ngrok")
            return None
        else:
            print(f"❌ Failed to get ngrok tunnels (status: {response.status_code})")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to ngrok API - is ngrok running?")
        return None
    except Exception as e:
        print(f"❌ Error getting ngrok URL: {e}")
        return None

def update_env_file(new_url):
    """Update the BASE_URL in the .env file."""
    env_file = Path(".env")
    
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
    
    print(f"✅ Updated .env file with BASE_URL={new_url}")

def main():
    parser = argparse.ArgumentParser(description="Update BASE_URL with current ngrok tunnel URL")
    parser.add_argument("--check-only", action="store_true", 
                       help="Only show current URLs without updating")
    args = parser.parse_args()
    
    # Get current environment BASE_URL
    current_env_url = os.getenv("BASE_URL", "Not set")
    print(f"🔍 Current BASE_URL in environment: {current_env_url}")
    
    # Get current ngrok URL
    print("🔍 Checking current ngrok tunnel...")
    ngrok_url = get_current_ngrok_url()
    
    if not ngrok_url:
        print("❌ Could not get ngrok URL - exiting")
        return 1
    
    print(f"🌐 Current ngrok tunnel URL: {ngrok_url}")
    
    if args.check_only:
        if current_env_url == ngrok_url:
            print("✅ URLs match - no update needed")
        else:
            print("⚠️  URLs don't match - run without --check-only to update")
        return 0
    
    # Check if update is needed
    if current_env_url == ngrok_url:
        print("✅ BASE_URL is already up to date!")
        return 0
    
    print(f"🔄 Updating BASE_URL from {current_env_url} to {ngrok_url}")
    
    # Update environment variable for current session
    os.environ["BASE_URL"] = ngrok_url
    print("✅ Updated BASE_URL in current environment")
    
    # Update .env file for persistence
    try:
        update_env_file(ngrok_url)
    except Exception as e:
        print(f"⚠️  Failed to update .env file: {e}")
        print("✅ Environment variable updated, but .env file unchanged")
        return 1
    
    print("🎉 BASE_URL update complete!")
    print(f"💡 Restart your shell or run 'source .env' to load the new URL in other sessions")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 