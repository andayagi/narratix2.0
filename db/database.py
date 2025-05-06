from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./narratix.db") # Default to SQLite

# Check if the URL is for SQLite and adjust if it's a relative path
if DATABASE_URL.startswith("sqlite:///") and not DATABASE_URL.startswith("sqlite:////"):
    # Construct absolute path for relative SQLite DBs
    # Assumes the db file is relative to the project root where .env might be
    # Adjust this logic if your db file location is different
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Go up two levels from db/database.py
    db_path = os.path.join(project_root, DATABASE_URL[len("sqlite:///"):])
    DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(DATABASE_URL)
# For SQLite, add connect_args to disable same-thread check if needed for FastAPI background tasks
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()