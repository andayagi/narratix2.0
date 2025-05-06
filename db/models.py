from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text as SQLAlchemyText, DateTime, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base

class Text(Base):
    __tablename__ = "texts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(SQLAlchemyText, nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analyzed = Column(Boolean, default=False, nullable=False)
    
    characters = relationship("Character", back_populates="text", cascade="all, delete-orphan")
    segments = relationship("TextSegment", back_populates="text_obj", cascade="all, delete-orphan")
    logs = relationship("ProcessLog", back_populates="text")

class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text_id = Column(Integer, ForeignKey("texts.id"))
    name = Column(String, nullable=False)
    description = Column(SQLAlchemyText, nullable=True)
    provider_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # New fields from first Anthropic call
    is_narrator = Column(Boolean, nullable=True)
    speaking = Column(Boolean, nullable=True)
    persona_description = Column(SQLAlchemyText, nullable=True)
    intro_text = Column(SQLAlchemyText, nullable=True)
    
    text = relationship("Text", back_populates="characters")
    segments = relationship("TextSegment", back_populates="character")

class TextSegment(Base):
    __tablename__ = "text_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text_id = Column(Integer, ForeignKey("texts.id"))
    character_id = Column(Integer, ForeignKey("characters.id"))
    text = Column(SQLAlchemyText, nullable=False)
    sequence = Column(Integer, nullable=False)
    audio_file = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # New fields from second Anthropic call
    description = Column(SQLAlchemyText, nullable=True)
    speed = Column(Float, nullable=True)
    trailing_silence = Column(Float, nullable=True)
    
    text_obj = relationship("Text", back_populates="segments")
    character = relationship("Character", back_populates="segments")

class ProcessLog(Base):
    __tablename__ = "process_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text_id = Column(Integer, ForeignKey("texts.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    operation = Column(String, nullable=False)
    request = Column(JSON, nullable=True)
    response = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    
    text = relationship("Text", back_populates="logs")