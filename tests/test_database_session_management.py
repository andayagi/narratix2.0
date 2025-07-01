"""
Test file for database session management improvements (Task 3).
Tests the new dependency injection patterns and session management utilities.
"""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from db.session_manager import (
    managed_db_session, 
    managed_db_transaction, 
    DatabaseSessionManager,
    DatabaseConnectionMonitor
)
from services.replicate_audio import SoundEffectProcessor, BackgroundMusicProcessor
from db import crud


class TestManagedDbSession:
    """Test the managed_db_session context manager."""
    
    def test_managed_db_session_commits_on_success(self):
        """Test that managed_db_session commits on successful execution."""
        with patch('db.session_manager.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_get_db.return_value = iter([mock_session])
            
            with managed_db_session() as db:
                assert db == mock_session
                # Simulate some database operation
                pass
            
            # Verify session was committed and closed
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
            mock_session.rollback.assert_not_called()
    
    def test_managed_db_session_rollback_on_exception(self):
        """Test that managed_db_session rolls back on exception."""
        with patch('db.session_manager.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_get_db.return_value = iter([mock_session])
            
            with pytest.raises(ValueError):
                with managed_db_session() as db:
                    assert db == mock_session
                    raise ValueError("Test exception")
            
            # Verify session was rolled back and closed
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
            mock_session.commit.assert_not_called()


class TestManagedDbTransaction:
    """Test the managed_db_transaction context manager."""
    
    def test_managed_db_transaction_commits_on_success(self):
        """Test that managed_db_transaction commits on successful execution."""
        mock_session = MagicMock()
        
        with managed_db_transaction(mock_session) as db:
            assert db == mock_session
            # Simulate some database operation
            pass
        
        # Verify session was committed but not closed (existing session)
        mock_session.commit.assert_called_once()
        mock_session.close.assert_not_called()
        mock_session.rollback.assert_not_called()
    
    def test_managed_db_transaction_rollback_on_exception(self):
        """Test that managed_db_transaction rolls back on exception."""
        mock_session = MagicMock()
        
        with pytest.raises(RuntimeError):
            with managed_db_transaction(mock_session) as db:
                assert db == mock_session
                raise RuntimeError("Test exception")
        
        # Verify session was rolled back but not closed (existing session)
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_not_called()
        mock_session.commit.assert_not_called()


class TestDatabaseSessionManager:
    """Test the DatabaseSessionManager utility class."""
    
    def test_safe_execute_success(self):
        """Test safe_execute with successful operation."""
        mock_session = MagicMock()
        mock_operation = MagicMock(return_value="success")
        
        result = DatabaseSessionManager.safe_execute(
            mock_session, 
            "test_operation", 
            mock_operation, 
            "arg1", 
            kwarg1="value1"
        )
        
        assert result == "success"
        mock_operation.assert_called_once_with(mock_session, "arg1", kwarg1="value1")
    
    def test_safe_execute_handles_exception(self):
        """Test safe_execute handles exceptions gracefully."""
        mock_session = MagicMock()
        mock_operation = MagicMock(side_effect=Exception("Test error"))
        
        result = DatabaseSessionManager.safe_execute(
            mock_session, 
            "test_operation", 
            mock_operation
        )
        
        assert result is None
        mock_operation.assert_called_once_with(mock_session)


class TestAudioProcessorDependencyInjection:
    """Test that audio processors correctly use dependency injection."""
    
    @patch('services.replicate_audio.managed_db_transaction')
    @patch('services.replicate_audio.crud.update_sound_effect_audio')
    @patch('services.replicate_audio.crud.create_log')
    def test_sound_effect_processor_uses_injected_session(self, mock_create_log, mock_update_audio, mock_transaction):
        """Test that SoundEffectProcessor uses injected database session."""
        mock_session = MagicMock()
        mock_transaction.__enter__ = MagicMock(return_value=mock_session)
        mock_transaction.__exit__ = MagicMock(return_value=None)
        mock_update_audio.return_value = True
        
        processor = SoundEffectProcessor()
        
        # Mock the parent class methods that would be called
        with patch.object(processor, '_download_audio', return_value=b'fake_audio'):
            with patch.object(processor, 'trim_audio', return_value=b'trimmed_audio'):
                
                db_session = MagicMock()
                result = processor.process_and_store(
                    db_session, 
                    123, 
                    {"id": "pred_123", "output": "http://example.com/audio.mp3"}
                )
                
                assert result is True
                # Verify transaction context manager was used
                mock_transaction.assert_called_with(db_session)
    
    @patch('services.replicate_audio.managed_db_transaction')
    @patch('services.replicate_audio.crud.update_text_background_music_audio')
    @patch('services.replicate_audio.crud.create_log')
    def test_background_music_processor_uses_injected_session(self, mock_create_log, mock_update_audio, mock_transaction):
        """Test that BackgroundMusicProcessor uses injected database session."""
        mock_session = MagicMock()
        mock_transaction.__enter__ = MagicMock(return_value=mock_session)
        mock_transaction.__exit__ = MagicMock(return_value=None)
        mock_update_audio.return_value = True
        
        processor = BackgroundMusicProcessor()
        
        # Mock the parent class methods that would be called
        with patch.object(processor, '_download_audio', return_value=b'fake_audio'):
            
            db_session = MagicMock()
            result = processor.process_and_store(
                db_session, 
                456, 
                {"id": "pred_456", "output": "http://example.com/music.mp3"}
            )
            
            assert result is True
            # Verify transaction context manager was used
            mock_transaction.assert_called_with(db_session)


class TestDatabaseConnectionMonitor:
    """Test database connection monitoring functionality."""
    
    def test_get_connection_pool_status(self):
        """Test getting connection pool status with real database."""
        # Test with the actual database engine - this verifies the integration
        status = DatabaseConnectionMonitor.get_connection_pool_status()
        
        # Verify the status has the expected keys
        assert "pool_type" in status
        assert "pool_size" in status
        assert "checked_in_connections" in status
        assert "checked_out_connections" in status
        assert "overflow_connections" in status
        assert "invalid_connections" in status
        
        # Verify values are correct types
        assert isinstance(status["pool_type"], str)
        assert isinstance(status["pool_size"], int)
        assert isinstance(status["checked_in_connections"], int)
        assert isinstance(status["checked_out_connections"], int)
        assert isinstance(status["overflow_connections"], int)
        assert isinstance(status["invalid_connections"], int)
        
        # For SQLite (StaticPool), verify expected values
        if status["pool_type"] == "StaticPool":
            assert status["pool_size"] == 1
            assert status["checked_in_connections"] == 0
            assert status["checked_out_connections"] == 1
            assert status["overflow_connections"] == 0
    
    @patch('db.session_manager.DatabaseConnectionMonitor.get_connection_pool_status')
    @patch('db.session_manager.logger')
    def test_log_connection_status(self, mock_logger, mock_get_status):
        """Test logging connection status."""
        mock_status = {"pool_size": 25, "checked_out": 5}
        mock_get_status.return_value = mock_status
        
        DatabaseConnectionMonitor.log_connection_status()
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "pool_status" in call_args[1]["extra"]


@pytest.mark.integration
class TestDatabaseSessionIntegration:
    """Integration tests for database session management."""
    
    def test_managed_session_with_real_database(self, db_session: Session):
        """Test managed session with real database operations."""
        # This test uses the pytest db_session fixture
        # which should work with our new session management
        
        from db import models
        
        # Test that we can perform database operations
        # This verifies that our session management doesn't break existing functionality
        text_count = db_session.query(models.Text).count()
        assert isinstance(text_count, int)
        
        # Test transaction rollback in the same session for proper isolation
        initial_count = db_session.query(models.Text).count()
        
        try:
            with managed_db_transaction(db_session) as tx_db:
                # Create a test record
                test_text = models.Text(title="Test Rollback", content="Test content for rollback")
                tx_db.add(test_text)
                tx_db.flush()  # This should assign an ID but not commit
                
                # Verify record exists within transaction
                current_count = tx_db.query(models.Text).count()
                assert current_count == initial_count + 1
                
                # Force an error to test rollback
                raise ValueError("Test rollback")
                
        except ValueError:
            pass  # Expected
        
        # Verify the record was not committed due to rollback
        # Refresh the session to see actual database state
        db_session.expire_all()
        final_count = db_session.query(models.Text).count()
        assert final_count == initial_count  # Should be the same as before 