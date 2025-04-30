"""Configuration for pytest."""
import os
import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import logging

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent)) 

from narratix.infrastructure.database.models import Base  # Adjust import if needed

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@pytest.fixture(scope="function")
def db_engine():
    """Yields a SQLAlchemy engine scoped to a test function."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)  # Create tables
    yield engine
    Base.metadata.drop_all(engine)    # Drop tables after test

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Yields a SQLAlchemy session scoped to a test function."""
    connection = db_engine.connect()
    # Begin a non-ORM transaction
    transaction = connection.begin()

    # Bind an individual Session to the connection
    TestingSessionLocal = sessionmaker(bind=connection, expire_on_commit=False)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Rollback the overall transaction
        transaction.rollback()
        connection.close()

@pytest.fixture(scope='session')
def db_session():
    # Placeholder for potential database session fixture setup if needed later
    print("\nSetting up DB session fixture (placeholder)")
    # Add actual DB setup/teardown here if required for tests
    yield None
    print("\nTearing down DB session fixture (placeholder)")

def pytest_sessionfinish(session):
    """
    Hook called after the whole test session finishes.
    Disables logging exceptions globally to prevent errors from loggers
    (like httpcore) attempting to write to closed streams during shutdown.
    See: https://github.com/pytest-dev/pytest/issues/5502
    """
    logging.raiseExceptions = False 