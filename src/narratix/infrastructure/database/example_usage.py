"""Example usage of the database configuration.

This module is for demonstration purposes only and should not be used in production.
"""

from .engine import Base, get_engine, create_tables
from .session import get_db_session

# Example of how to define a model
from sqlalchemy import Column, Integer, String


class ExampleModel(Base):
    """Example model for demonstration purposes."""
    
    __tablename__ = "example"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)


def example_usage():
    """Example of how to use the database session."""
    # Create tables if they don't exist
    create_tables()
    
    # Using the session context manager
    with get_db_session() as session:
        # Example of creating a new record
        new_item = ExampleModel(name="Example Item", description="This is an example")
        session.add(new_item)
        
        # Example of querying data
        all_items = session.query(ExampleModel).all()
        for item in all_items:
            print(f"Item: {item.name} - {item.description}")
            
    # Session is automatically closed when the context manager exits 