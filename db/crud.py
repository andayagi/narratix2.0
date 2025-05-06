from sqlalchemy.orm import Session
import uuid
from . import models
from typing import List, Optional, Dict, Any

# Text CRUD
def create_text(db: Session, content: str, title: Optional[str] = None) -> models.Text:
    db_text = models.Text(content=content, title=title)
    db.add(db_text)
    db.commit()
    db.refresh(db_text)
    return db_text

def get_text(db: Session, text_id: uuid.UUID) -> Optional[models.Text]:
    return db.query(models.Text).filter(models.Text.id == text_id).first()

def get_text_by_content(db: Session, content: str) -> Optional[models.Text]:
    return db.query(models.Text).filter(models.Text.content == content).first()

def update_text_analyzed(db: Session, text_id: uuid.UUID, analyzed: bool) -> Optional[models.Text]:
    db_text = get_text(db, text_id)
    if db_text:
        db_text.analyzed = analyzed
        db.commit()
        db.refresh(db_text)
    return db_text

# Character CRUD
def create_character(
    db: Session, 
    text_id: str, 
    name: str,
    description: Optional[str] = None,
    is_narrator: Optional[bool] = None,
    speaking: Optional[bool] = None,
    intro_text: Optional[str] = None,
    provider_id: Optional[str] = None 
) -> models.Character:
    db_character = models.Character(
        text_id=text_id,
        name=name,
        description=description, 
        provider_id=provider_id,
        is_narrator=is_narrator,
        speaking=speaking,
        intro_text=intro_text
    )
    db.add(db_character)
    db.commit()
    db.refresh(db_character)
    return db_character

def get_characters_by_text(db: Session, text_id: uuid.UUID) -> List[models.Character]:
    return db.query(models.Character).filter(models.Character.text_id == text_id).all()

def update_character_voice(db: Session, character_id: uuid.UUID, provider_id: str) -> Optional[models.Character]:
    db_character = db.query(models.Character).filter(models.Character.id == character_id).first()
    if db_character:
        db_character.provider_id = provider_id
        db.commit()
        db.refresh(db_character)
    return db_character

# TextSegment CRUD
def create_text_segment(
    db: Session,
    text_id: str, # Assume ID is string from process_text_analysis
    character_id: str, # Assume ID is string from character map
    # content: str, # Renamed to text
    text: str,
    sequence: int,
    # audio_file: Optional[str] = None, # Keep for TTS
    description: Optional[str] = None, # Acting instructions
    speed: Optional[float] = None,
    trailing_silence: Optional[float] = None,
    audio_file: Optional[str] = None # Keep audio_file for potential future use
) -> models.TextSegment:
    db_segment = models.TextSegment(
        text_id=text_id, # Should be UUID
        character_id=character_id, # Should be UUID
        # content=content, # Renamed
        text=text,
        sequence=sequence,
        audio_file=audio_file,
        description=description,
        speed=speed,
        trailing_silence=trailing_silence
    )
    db.add(db_segment)
    db.commit()
    db.refresh(db_segment)
    return db_segment

def get_segments_by_text(db: Session, text_id: uuid.UUID) -> List[models.TextSegment]:
    return db.query(models.TextSegment).filter(
        models.TextSegment.text_id == text_id
    ).order_by(models.TextSegment.sequence).all()

def update_segment_audio(db: Session, segment_id: uuid.UUID, audio_file: str) -> Optional[models.TextSegment]:
    db_segment = db.query(models.TextSegment).filter(models.TextSegment.id == segment_id).first()
    if db_segment:
        db_segment.audio_file = audio_file
        db.commit()
        db.refresh(db_segment)
    return db_segment

# ProcessLog CRUD
def create_log(
    db: Session,
    operation: str,
    status: str,
    text_id: Optional[uuid.UUID] = None,
    request: Optional[Dict[str, Any]] = None,
    response: Optional[Dict[str, Any]] = None
) -> models.ProcessLog:
    db_log = models.ProcessLog(
        text_id=text_id,
        operation=operation,
        status=status,
        request=request,
        response=response
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log