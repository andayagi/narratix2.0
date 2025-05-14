#!/usr/bin/env python3

import subprocess
import sys
import os

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def main():
    """Run Alembic migrations to latest version"""
    try:
        print("Running Alembic migrations to 'heads' (multiple heads support)...")
        result = subprocess.run(
            ["alembic", "upgrade", "heads"],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("Migrations completed successfully.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error running migrations: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 