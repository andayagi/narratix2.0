#!/usr/bin/env python
"""
Narratix 2.0 Setup Script
-------------------------
This script sets up the basic structure for the Narratix 2.0 project.
It creates the necessary directories and initial files.
"""

import os
import sys
import shutil
from pathlib import Path
import subprocess

# Define the project structure
PROJECT_STRUCTURE = {
    "api": {
        "__init__.py": "",
        "main.py": "",
        "endpoints": {
            "__init__.py": "",
            "text.py": "",
            "character.py": "",
            "audio.py": ""
        }
    },
    "db": {
        "__init__.py": "",
        "database.py": "",
        "models.py": "",
        "crud.py": ""
    },
    "services": {
        "__init__.py": "",
        "text_analysis.py": "",
        "voice_generation.py": "",
        "audio_generation.py": ""
    },
    "utils": {
        "__init__.py": "",
        "logging.py": "",
        "config.py": ""
    },
    "alembic": {},
    "tests": {
        "__init__.py": "",
        "test_basic_flow.py": ""
    },
    "audio_files": {},
    "logs": {
        "api_calls": {}
    }
}

# Sample .env file content
ENV_CONTENT = """# Database
# Use SQLite by default, in the db/ directory
DATABASE_URL=sqlite:///./db/narratix.db

# API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key
HUME_API_KEY=your_hume_api_key

# Paths
AUDIO_STORAGE_PATH=audio_files

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/narratix.log
"""

# Sample .gitignore content
GITIGNORE_CONTENT = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.venv
env/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Project specific
logs/
audio_files/
.DS_Store
"""

# Sample requirements.txt content
REQUIREMENTS_CONTENT = """fastapi==0.115.0
uvicorn==0.30.0
sqlalchemy==2.0.28
alembic==1.13.1
pydantic==2.6.1
python-dotenv==1.0.1
anthropic==0.21.0
httpx==0.27.0
# psycopg2-binary==2.9.9 # Removed for SQLite
python-multipart==0.0.9
uuid==1.30
pytest==7.4.3
"""

def create_directory_structure(base_path, structure, current_path=""):
    """Create the directory structure recursively."""
    for name, content in structure.items():
        path = os.path.join(base_path, current_path, name)
        
        if isinstance(content, dict):
            # It's a directory
            os.makedirs(path, exist_ok=True)
            create_directory_structure(base_path, content, os.path.join(current_path, name))
        else:
            # It's a file
            with open(path, "w") as f:
                f.write(content)

def create_project_files(base_path):
    """Create project-specific files."""
    # Create .env file
    with open(os.path.join(base_path, ".env"), "w") as f:
        f.write(ENV_CONTENT)
    
    # Create .gitignore
    with open(os.path.join(base_path, ".gitignore"), "w") as f:
        f.write(GITIGNORE_CONTENT)
    
    # Create requirements.txt
    with open(os.path.join(base_path, "requirements.txt"), "w") as f:
        f.write(REQUIREMENTS_CONTENT)
    
    # Create empty main.py
    with open(os.path.join(base_path, "main.py"), "w") as f:
        f.write("import uvicorn\nfrom api.main import app\n\nif __name__ == \"__main__\":\n    uvicorn.run(\"api.main:app\", host=\"0.0.0.0\", port=8000, reload=True)\n")

def setup_virtual_environment(base_path):
    """Set up a virtual environment and install dependencies."""
    try:
        print("Setting up virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", os.path.join(base_path, "venv")], check=True)
        
        # Determine the pip path
        if sys.platform == "win32":
            pip_path = os.path.join(base_path, "venv", "Scripts", "pip")
        else:
            pip_path = os.path.join(base_path, "venv", "bin", "pip")
        
        print("Installing dependencies...")
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
        subprocess.run([pip_path, "install", "-r", os.path.join(base_path, "requirements.txt")], check=True)
        
        print("Virtual environment setup complete!")
    except subprocess.CalledProcessError as e:
        print(f"Error setting up virtual environment: {e}")
        return False
    
    return True

def main():
    # Get the base path (current directory or specified)
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        base_path = os.getcwd()
    
    print(f"Setting up Narratix 2.0 project at: {base_path}")
    
    # Create directory structure
    create_directory_structure(base_path, PROJECT_STRUCTURE)
    print("Directory structure created.")
    
    # Create project files
    create_project_files(base_path)
    print("Project files created.")
    
    # Ask if virtual environment should be set up
    setup_venv = input("Do you want to set up a virtual environment? (y/n): ").lower() == 'y'
    if setup_venv:
        setup_virtual_environment(base_path)
    
    print("\nNarratix 2.0 project setup complete!")
    print("\nNext steps:")
    print("1. Edit .env file with your actual database URL and API keys")
    print("2. Follow the implementation guide to add code to each file")
    print("3. Run `python main.py` to start the application")

if __name__ == "__main__":
    main()