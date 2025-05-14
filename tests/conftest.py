import sys
import os
import pytest
from datetime import datetime

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Initialize logging module before importing other modules
from utils.logging import SessionLogger
SessionLogger.start_session()

from db.database import SessionLocal, engine, Base
from db import models, crud

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Register custom markers
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test that may interact with external services"
    )

@pytest.fixture
def db_session():
    """Provides a SQLAlchemy session for tests"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 