#!/usr/bin/env python
"""Generate initial Alembic migration.

This script generates the initial Alembic migration based on the defined SQLAlchemy models.
It should be run after defining your models but before running any database operations.
"""

import os
import sys
import subprocess

def main():
    """Generate the initial migration."""
    # Generate a migration with the message 'initial'
    subprocess.run([
        "alembic", 
        "revision", 
        "--autogenerate", 
        "-m", "initial"
    ], check=True)
    
    print("Migration generated successfully.")
    print("To apply migrations, run: alembic upgrade head")


if __name__ == "__main__":
    # Make sure we're in the migrations directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Run the migration generator
    main() 