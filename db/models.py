from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text as SQLAlchemyText, DateTime, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import math

from .database import Base

class Text(Base):
    __tablename__ = "texts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(SQLAlchemyText, nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    analyzed = Column(Boolean, default=False, nullable=False)
    background_music_prompt = Column(SQLAlchemyText, nullable=True)
    background_music_audio_b64 = Column(SQLAlchemyText, nullable=True)
    bg_audio_timestamp = Column(DateTime(timezone=True), nullable=True)  # When background music audio was last created
    word_timestamps = Column(JSON, nullable=True)  # Store complete word-level timing data
    force_alignment_timestamp = Column(DateTime(timezone=True), nullable=True)  # When force alignment was last performed
    
    characters = relationship("Character", back_populates="text", cascade="all, delete-orphan")
    segments = relationship("TextSegment", back_populates="text_obj", cascade="all, delete-orphan")
    logs = relationship("ProcessLog", back_populates="text")
    sound_effects = relationship("SoundEffect", back_populates="text", cascade="all, delete-orphan")

class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text_id = Column(Integer, ForeignKey("texts.id"))
    name = Column(String, nullable=False)
    description = Column(SQLAlchemyText, nullable=True)
    provider_id = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
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
    audio_data_b64 = Column(SQLAlchemyText, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # New fields from second Anthropic call
    description = Column(SQLAlchemyText, nullable=True)
    speed = Column(Float, nullable=True)
    trailing_silence = Column(Float, nullable=True)
    
    text_obj = relationship("Text", back_populates="segments")
    character = relationship("Character", back_populates="segments")
    sound_effects = relationship("SoundEffect", back_populates="segment", cascade="all, delete-orphan")

class SoundEffect(Base):
    __tablename__ = "sound_effects"
    
    effect_id = Column(Integer, primary_key=True, autoincrement=True)
    effect_name = Column(String, nullable=False)
    text_id = Column(Integer, ForeignKey("texts.id"), nullable=False)
    segment_id = Column(Integer, ForeignKey("text_segments.id"), nullable=True)
    start_word = Column(String, nullable=False)
    end_word = Column(String, nullable=False)
    start_word_position = Column(Integer, nullable=True)  # Position of start word in text
    end_word_position = Column(Integer, nullable=True)    # Position of end word in text
    prompt = Column(SQLAlchemyText, nullable=False)
    audio_data_b64 = Column(SQLAlchemyText, nullable=True)
    start_time = Column(Float, nullable=True)  # From force alignment
    end_time = Column(Float, nullable=True)    # From force alignment
    total_time = Column(Integer, nullable=True)  # Calculated total time in seconds (rounded, min 1)
    rank = Column(Integer, nullable=True)  # Importance ranking from Claude analysis (1 = most important)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    audio_timestamp = Column(DateTime(timezone=True), nullable=True)  # When audio was last created
    
    # Relationships
    text = relationship("Text", back_populates="sound_effects")
    segment = relationship("TextSegment", back_populates="sound_effects")

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