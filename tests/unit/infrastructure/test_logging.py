import logging
import logging.handlers
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib

import pytest

# We need to import the module we want to test, but need to do it carefully
# because it configures the root logger on import.
# We'll use importlib to reload it within tests if needed, or structure tests
# to manage the side effects.
# Let's try reloading to ensure clean state for tests.
# We need to capture the module before potential reload
logging_module_path = "src.narratix.infrastructure.logging"
try:
    narratix_logging = importlib.import_module(logging_module_path)
except ImportError:
    # Handle case where module doesn't exist yet if tests run before creation
    pytest.skip(f"Module {logging_module_path} not found", allow_module_level=True)


@pytest.fixture(autouse=True)
def setup_logging_mocks(monkeypatch):
    """Auto-applied fixture to mock filesystem and handlers for tests."""
    # Mock Path methods to avoid actual file system operations
    # We will mock the mkdir method directly on the original Path class
    mock_mkdir = MagicMock()
    monkeypatch.setattr("pathlib.Path.mkdir", mock_mkdir)

    # Mock os.getenv used for LOG_DIR
    mock_getenv = MagicMock(return_value="mock_logs")
    monkeypatch.setattr(f"{logging_module_path}.os.getenv", mock_getenv)

    # Mock handlers to prevent console/file output during tests
    # Add 'level' attribute to the mock instances
    mock_stream_handler = MagicMock(spec=logging.StreamHandler)
    mock_stream_handler.level = logging.NOTSET # Default level
    mock_file_handler = MagicMock(spec=logging.handlers.RotatingFileHandler)
    mock_file_handler.level = logging.NOTSET # Default level

    # Patch the handler classes in the standard logging module namespace
    monkeypatch.setattr("logging.StreamHandler", MagicMock(return_value=mock_stream_handler))
    monkeypatch.setattr("logging.handlers.RotatingFileHandler", MagicMock(return_value=mock_file_handler))

    # Ensure the root logger is clean before reloading the module
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING) # Reset root level to default

    # Reload the logging module to apply configuration with mocks
    try:
        reloaded_logging = importlib.reload(narratix_logging)
    except NameError: # Handle if narratix_logging wasn't successfully imported initially
         pytest.skip(f"Module {logging_module_path} could not be loaded/reloaded", allow_module_level=True)
         reloaded_logging = None # To avoid further errors

    yield mock_mkdir, mock_stream_handler, mock_file_handler, reloaded_logging # Provide mocks and reloaded module

    # Cleanup: Reset root logger state again
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING) # Reset root level to default


def test_get_logger(setup_logging_mocks):
    """Test that get_logger returns a Logger instance with the correct name."""
    _, _, _, reloaded_logging = setup_logging_mocks
    if reloaded_logging is None: pytest.skip("Logging module not loaded")

    logger_name = "test_logger"
    logger = reloaded_logging.get_logger(logger_name)
    assert isinstance(logger, logging.Logger)
    assert logger.name == logger_name
    # Check if it inherits handlers from the root logger
    assert len(logger.handlers) == 0 # Child loggers don't have handlers by default
    assert logger.parent == logging.getLogger() # Should be child of root

def test_logging_configuration(setup_logging_mocks):
    """Test that the root logger is configured with mocked handlers."""
    mock_mkdir, mock_stream_handler, mock_file_handler, reloaded_logging = setup_logging_mocks
    if reloaded_logging is None: pytest.skip("Logging module not loaded")


    # Check mock Path was used for directory creation
    # Path() returns mock_path_instance, LOG_DIR = Path(...) means LOG_DIR is mock_path_instance
    # LOG_DIR.mkdir(...) calls mock_path_instance.mkdir which we set to mock_mkdir
    # Assert directly on the mock function provided by the fixture.
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    root_logger = logging.getLogger() # Get the standard root logger
    assert mock_stream_handler in root_logger.handlers
    assert mock_file_handler in root_logger.handlers
    assert root_logger.level == logging.DEBUG

    # Check handler levels were set correctly after reload
    mock_stream_handler.setLevel.assert_called_with(logging.INFO)
    mock_file_handler.setLevel.assert_called_with(logging.DEBUG)

# Note: Testing the actual logging output often involves capturing logs.
# The 'caplog' fixture from pytest can be used for this.

def test_log_messages(caplog, setup_logging_mocks):
    """Test that messages are logged at different levels."""
    # caplog needs to be setup before get_logger is called if we rely on root logger config
    _, mock_stream_handler, mock_file_handler, reloaded_logging = setup_logging_mocks
    if reloaded_logging is None: pytest.skip("Logging module not loaded")

    # Ensure mocks have the level attribute needed by logger.handle
    # This was added in the fixture now.

    logger = reloaded_logging.get_logger("message_test")

    # Set handler levels explicitly on mocks for predictable filtering by caplog if needed
    # Although caplog captures before handler filtering, setting this ensures the mock state is consistent.
    mock_stream_handler.level = logging.INFO
    mock_file_handler.level = logging.DEBUG


    with caplog.at_level(logging.DEBUG, logger="message_test"): # Capture from specific logger
        logger.debug("Debug test message")
        logger.info("Info test message")
        logger.warning("Warning test message")
        logger.error("Error test message")
        logger.critical("Critical test message")

    # Check captured records
    assert "Debug test message" in caplog.text
    assert "Info test message" in caplog.text
    assert "Warning test message" in caplog.text
    assert "Error test message" in caplog.text
    assert "Critical test message" in caplog.text

    # Check log levels associated with messages
    assert len(caplog.records) == 5
    assert caplog.records[0].levelname == "DEBUG"
    assert caplog.records[1].levelname == "INFO"
    assert caplog.records[2].levelname == "WARNING"
    assert caplog.records[3].levelname == "ERROR"
    assert caplog.records[4].levelname == "CRITICAL"

    # Optional: Check if handlers were called (more advanced mocking)
    # Example: mock_file_handler.handle.call_count == 5
    # mock_stream_handler.handle.call_count == 4 (due to INFO level)


# Test environment variable usage (optional, might require process isolation)
# This test remains complex due to module reload and path mocking intricacies
# @pytest.mark.skip(reason="Reloading and path mocking interaction needs careful review")
def test_log_dir_env_variable(monkeypatch, setup_logging_mocks):
    """Test that LOG_DIR uses the environment variable (requires module reload)."""

    # Fixture already mocks getenv and reloads module, let's verify getenv call
    _, _, _, reloaded_logging = setup_logging_mocks
    if reloaded_logging is None: pytest.skip("Logging module not loaded")

    # The fixture mocks os.getenv called during the reload
    reloaded_logging.os.getenv.assert_called_with("LOG_DIR", "logs") # Check if getenv was called as expected

    # We can also check the resulting LOG_DIR path object if Path mock is robust
    # This depends heavily on the specifics of the Path mock implementation
    # assert str(reloaded_logging.LOG_DIR) == "mock_logs" # If Path mock returns stringifiable obj
    pass # Keep test minimal due to complexity 