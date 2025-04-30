# Database Configuration for Narratix

This module contains the SQLAlchemy configuration for the Narratix application.

## Overview

The database layer is designed with the following features:

- Environment-based configuration using environment variables
- Session factory pattern for creating database sessions
- Thread-local engine instances for thread safety
- Support for SQLite (development) and PostgreSQL (production)
- Alembic integration for database migrations

## Usage

### Basic Database Operations

```python
from narratix.infrastructure.database import get_db_session
from narratix.infrastructure.database.engine import create_tables

# Create tables (if needed)
create_tables()

# Using the session
with get_db_session() as session:
    # Perform database operations
    result = session.query(YourModel).filter(YourModel.id == 1).first()
    
    # Add new records
    new_record = YourModel(name="Example")
    session.add(new_record)
    # Commit happens automatically when the context manager exits
```

### Defining Models

Models should inherit from the Base class:

```python
from narratix.infrastructure.database.engine import Base
from sqlalchemy import Column, Integer, String

class YourModel(Base):
    __tablename__ = "your_table"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
```

## Configuration

Database settings are configured through environment variables in `.env` file:

- `DATABASE_URL`: Connection string (defaults to SQLite)
- `DATABASE_ECHO`: Enable SQL query logging (true/false)
- `DATABASE_POOL_SIZE`: Connection pool size
- `DATABASE_POOL_TIMEOUT`: Connection timeout in seconds
- `DATABASE_POOL_RECYCLE`: Connection recycle time in seconds
- `DATABASE_MAX_OVERFLOW`: Max connections beyond pool size

## Migrations

Database migrations are managed with Alembic:

1. To generate a migration: `cd migrations && python -m create_migration.py`
2. To apply migrations: `cd migrations && alembic upgrade head`
3. To downgrade: `cd migrations && alembic downgrade -1` 