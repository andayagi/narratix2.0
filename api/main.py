from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import os

from .endpoints import text, character, audio
from db.database import engine, Base
from utils.config import settings
from utils.logging import SessionLogger
import utils.http_client

# Start API session only if no session exists (preserve test session when under pytest)
existing_session = SessionLogger.get_current_session()
if not existing_session:
    api_session_id = SessionLogger.start_session("api_server")
else:
    api_session_id = existing_session

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Narratix API",
    description="API for Narratix text-to-audio conversion",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(text.router)
app.include_router(character.router)
app.include_router(audio.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Narratix API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}