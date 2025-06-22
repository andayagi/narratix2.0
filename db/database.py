from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./db/narratix.db") # Default to SQLite in db/ directory

# Check if the URL is for SQLite and adjust if it's a relative path
if DATABASE_URL.startswith("sqlite:///") and not DATABASE_URL.startswith("sqlite:////"):
    # Construct absolute path for relative SQLite DBs
    # Assumes the db file is relative to the project root where .env might be
    # Adjust this logic if your db file location is different
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Go up two levels from db/database.py
    db_path = os.path.join(project_root, DATABASE_URL[len("sqlite:///"):])
    DATABASE_URL = f"sqlite:///{db_path}"

# Enhanced database configuration for parallel processing
if DATABASE_URL.startswith("sqlite"):
    # For SQLite, add connect_args to disable same-thread check and enable WAL mode for better concurrency
    engine = create_engine(
        DATABASE_URL, 
        connect_args={
            "check_same_thread": False,
            "timeout": 20  # 20 second timeout for SQLite connections
        },
        pool_size=25,           # Increased for parallel operations
        max_overflow=35,        # Higher burst capacity  
        pool_pre_ping=True,     # Verify connection health
        pool_recycle=3600       # Refresh connections hourly
    )
else:
    # For PostgreSQL/MySQL with full parallel processing support
    engine = create_engine(
        DATABASE_URL,
        pool_size=25,           # Increased for parallel operations
        max_overflow=35,        # Higher burst capacity
        pool_pre_ping=True,     # Verify connection health
        pool_recycle=3600       # Refresh connections hourly
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()