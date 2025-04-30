"""Database session management module."""

import contextlib
from typing import Iterator, Callable, Any

from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession

from .engine import get_engine

# Type alias for Session
Session = SQLAlchemySession


def get_session_factory() -> Callable[..., Session]:
    """
    Get a session factory that creates new database sessions.
    
    Returns:
        Callable: A session factory function.
    """
    engine = get_engine()
    factory = sessionmaker(
        bind=engine, 
        autocommit=False, 
        autoflush=False, 
        expire_on_commit=False
    )
    return factory


@contextlib.contextmanager
def get_db_session() -> Iterator[Session]:
    """
    Context manager that provides a database session.
    
    Yields:
        Session: Database session for executing queries.
        
    Example:
        ```
        with get_db_session() as session:
            result = session.query(Model).all()
        ```
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close() 