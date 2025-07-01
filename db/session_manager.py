"""
Database session management utilities for improved transaction handling and dependency injection.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from db.database import get_db
from utils.logging import get_logger

logger = get_logger(__name__)

@contextmanager
def managed_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic cleanup and transaction management.
    
    Features:
    - Automatic commit/rollback
    - Proper session cleanup
    - Error logging
    - Transaction isolation
    
    Yields:
        SQLAlchemy Session with automatic transaction management
        
    Example:
        with managed_db_session() as db:
            result = crud.get_text(db, text_id)
        # Session is automatically committed and closed
    """
    db = next(get_db())
    try:
        yield db
        db.commit()  # Commit any pending transactions
        logger.debug("Database transaction committed successfully")
    except SQLAlchemyError as e:
        db.rollback()  # Rollback on SQLAlchemy errors
        logger.error(f"SQLAlchemy error, rolling back transaction: {e}")
        raise
    except Exception as e:
        db.rollback()  # Rollback on any other exception
        logger.error(f"Unexpected error, rolling back transaction: {e}")
        raise
    finally:
        db.close()  # Always close the session
        logger.debug("Database session closed")

@contextmanager
def managed_db_transaction(db: Session) -> Generator[Session, None, None]:
    """
    Context manager for explicit transaction management with an existing session.
    
    This is used when you already have a database session but want to ensure
    proper transaction boundaries for a specific operation.
    
    Args:
        db: Existing database session
        
    Yields:
        The same database session with transaction management
        
    Example:
        with managed_db_transaction(db) as tx_db:
            crud.update_something(tx_db, ...)
            crud.create_something_else(tx_db, ...)
        # Transaction is committed or rolled back automatically
    """
    try:
        yield db
        db.commit()
        logger.debug("Explicit transaction committed successfully")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"SQLAlchemy error in explicit transaction, rolling back: {e}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in explicit transaction, rolling back: {e}")
        raise

class DatabaseSessionManager:
    """
    Utility class for managing database sessions across services.
    Provides consistent session management patterns and dependency injection support.
    """
    
    @staticmethod
    def create_session() -> Session:
        """
        Create a new database session.
        
        Returns:
            New SQLAlchemy session (caller responsible for closing)
        """
        return next(get_db())
    
    @staticmethod
    @contextmanager
    def session_scope() -> Generator[Session, None, None]:
        """
        Alternative session context manager with the same functionality as managed_db_session.
        
        Yields:
            SQLAlchemy Session with automatic transaction management
        """
        with managed_db_session() as db:
            yield db
    
    @staticmethod
    def safe_execute(db: Session, operation_name: str, operation_func, *args, **kwargs) -> Optional[Any]:
        """
        Safely execute a database operation with proper error handling and logging.
        
        Args:
            db: Database session to use
            operation_name: Descriptive name for logging
            operation_func: Function to execute
            *args: Arguments to pass to operation_func
            **kwargs: Keyword arguments to pass to operation_func
            
        Returns:
            Result from operation_func or None if error occurred
        """
        try:
            logger.debug(f"Executing database operation: {operation_name}")
            result = operation_func(db, *args, **kwargs)
            logger.debug(f"Database operation completed successfully: {operation_name}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy error in operation '{operation_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in operation '{operation_name}': {e}")
            return None

class DatabaseConnectionMonitor:
    """
    Monitor database connection health and provide connection pool statistics.
    """
    
    @staticmethod
    def get_connection_pool_status() -> Dict[str, Any]:
        """
        Get current connection pool status for monitoring.
        
        Returns:
            Dictionary with connection pool statistics
        """
        from db.database import engine
        from sqlalchemy.pool import StaticPool
        
        pool = engine.pool
        
        # StaticPool (SQLite) and QueuePool (PostgreSQL/MySQL) have different methods
        if isinstance(pool, StaticPool):
            # SQLite StaticPool has limited monitoring capabilities
            return {
                "pool_type": "StaticPool",
                "pool_size": 1,  # StaticPool always has 1 connection
                "checked_in_connections": 0,  # Not applicable for StaticPool
                "checked_out_connections": 1,  # Always 1 for StaticPool
                "overflow_connections": 0,  # Not applicable for StaticPool
                "invalid_connections": 0,  # Not easily detectable for StaticPool
            }
        else:
            # QueuePool and other pools support full monitoring
            return {
                "pool_type": type(pool).__name__,
                "pool_size": pool.size(),
                "checked_in_connections": pool.checkedin(),
                "checked_out_connections": pool.checkedout(),
                "overflow_connections": pool.overflow(),
                "invalid_connections": pool.invalid(),
            }
    
    @staticmethod
    def log_connection_status():
        """Log current connection pool status for debugging."""
        status = DatabaseConnectionMonitor.get_connection_pool_status()
        logger.info("Database connection pool status", extra={"pool_status": status})

# Backwards compatibility - re-export the main function
__all__ = [
    'managed_db_session',
    'managed_db_transaction', 
    'DatabaseSessionManager',
    'DatabaseConnectionMonitor'
] 