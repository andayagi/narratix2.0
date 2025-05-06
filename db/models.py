from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text as SQLAlchemyText, DateTime, JSON, Float, UUID
# from sqlalchemy.dialects.postgresql import UUID # Removed for SQLite compatibility
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .database import Base

class Text(Base):
    __tablename__ = "texts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(SQLAlchemyText, nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analyzed = Column(Boolean, default=False)
    
    characters = relationship("Character", back_populates="text", cascade="all, delete-orphan")
    segments = relationship("TextSegment", back_populates="text_obj", cascade="all, delete-orphan")
    logs = relationship("ProcessLog", back_populates="text")

class Character(Base):
    __tablename__ = "characters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text_id = Column(UUID(as_uuid=True), ForeignKey("texts.id"))
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text_id = Column(UUID(as_uuid=True), ForeignKey("texts.id"))
    character_id = Column(UUID(as_uuid=True), ForeignKey("characters.id"))
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text_id = Column(UUID(as_uuid=True), ForeignKey("texts.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    operation = Column(String, nullable=False)
    request = Column(JSON, nullable=True)
    response = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    
    text = relationship("Text", back_populates="logs")