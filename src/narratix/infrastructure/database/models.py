"""SQLAlchemy database models for the Narratix application."""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from sqlalchemy import String, Integer, Float, Boolean, Text, JSON, ForeignKey, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .engine import Base


class TextContent(Base):
    """
    SQLAlchemy model for text content to be processed.
    
    Represents the input text for narrative processing.
    """
    __tablename__ = "text_contents"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    content_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    narrative_elements: Mapped[list["NarrativeElement"]] = relationship(
        "NarrativeElement", back_populates="text_content", cascade="all, delete-orphan"
    )


class Voice(Base):
    """
    SQLAlchemy model for TTS voice profiles.
    
    Represents a specific Text-to-Speech (TTS) voice configuration.
    """
    __tablename__ = "voices"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    voice_id: Mapped[str] = mapped_column(String(100), nullable=False)
    voice_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )
    accent: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    voice_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    pitch: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    characters: Mapped[list["Character"]] = relationship(
        "Character", back_populates="voice"
    )


class Character(Base):
    """
    SQLAlchemy model for narrative characters.
    
    Represents a distinct character voice within the text.
    """
    __tablename__ = "characters"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voices.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    voice: Mapped[Optional["Voice"]] = relationship(
        "Voice", back_populates="characters"
    )
    narrative_elements: Mapped[list["NarrativeElement"]] = relationship(
        "NarrativeElement", back_populates="character"
    )


class NarrativeElement(Base):
    """
    SQLAlchemy model for narrative elements.
    
    Represents a segment of text assigned to a specific character or narrative role.
    """
    __tablename__ = "narrative_elements"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    text_segment: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    element_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    acting_instructions: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    speed: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )
    trailing_silence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    text_content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("text_contents.id"), nullable=False
    )
    character_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    text_content: Mapped["TextContent"] = relationship(
        "TextContent", back_populates="narrative_elements"
    )
    character: Mapped[Optional["Character"]] = relationship(
        "Character", back_populates="narrative_elements"
    ) 