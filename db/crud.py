from sqlalchemy.orm import Session
from . import models
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Text CRUD
def create_text(db: Session, content: str, title: Optional[str] = None) -> models.Text:
    db_text = models.Text(content=content, title=title)
    db.add(db_text)
    db.commit()
    db.refresh(db_text)
    return db_text

def get_text(db: Session, text_id: int) -> Optional[models.Text]:
    return db.query(models.Text).filter(models.Text.id == text_id).first()

def get_text_by_content(db: Session, content: str) -> Optional[models.Text]:
    return db.query(models.Text).filter(models.Text.content == content).first()

def update_text_analyzed(db: Session, text_id: int, analyzed: bool) -> Optional[models.Text]:
    db_text = get_text(db, text_id)
    if db_text:
        db_text.analyzed = analyzed
        db.commit()
        db.refresh(db_text)
    return db_text

def update_text_background_music_audio(db: Session, text_id: int, audio_data_b64: str) -> Optional[models.Text]:
    """
    Update the background_music_audio_b64 field for a text.
    
    Args:
        db: Database session
        text_id: ID of the text to update
        audio_data_b64: Base64 encoded audio data
        
    Returns:
        Updated Text object or None if text not found
    """
    db_text = get_text(db, text_id)
    if db_text:
        db_text.background_music_audio_b64 = audio_data_b64
        db.commit()
        db.refresh(db_text)
    return db_text

def update_text_word_timestamps(db: Session, text_id: int, word_timestamps: List[Dict]) -> Optional[models.Text]:
    """
    Update the word_timestamps field for a text and set force_alignment_timestamp.
    
    Args:
        db: Database session
        text_id: ID of the text to update
        word_timestamps: List of word timestamp dictionaries
        
    Returns:
        Updated Text object or None if text not found
    """
    db_text = get_text(db, text_id)
    if db_text:
        db_text.word_timestamps = word_timestamps
        db_text.force_alignment_timestamp = datetime.utcnow()
        db.commit()
        db.refresh(db_text)
    return db_text

def clear_text_word_timestamps(db: Session, text_id: int) -> Optional[models.Text]:
    """
    Clear force alignment data for a text (both timestamps and alignment timestamp).
    
    Args:
        db: Database session
        text_id: ID of the text to clear alignment for
        
    Returns:
        Updated Text object or None if text not found
    """
    db_text = get_text(db, text_id)
    if db_text:
        db_text.word_timestamps = None
        db_text.force_alignment_timestamp = None
        db.commit()
        db.refresh(db_text)
    return db_text

def is_force_alignment_valid(db: Session, text_id: int) -> bool:
    """
    Check if force alignment is valid (alignment timestamp is newer than all segment timestamps).
    
    Args:
        db: Database session
        text_id: ID of the text to check alignment validity for
        
    Returns:
        True if alignment is valid and current, False otherwise
    """
    db_text = get_text(db, text_id)
    if not db_text or not db_text.force_alignment_timestamp or not db_text.word_timestamps:
        return False
    
    # Get all segments for this text
    segments = get_segments_by_text(db, text_id)
    if not segments:
        return True  # No segments to compare against
    
    # Check if any segment was updated after the alignment
    for segment in segments:
        if segment.last_updated > db_text.force_alignment_timestamp:
            return False
    
    return True

# Character CRUD
def create_character(
    db: Session, 
    text_id: int, 
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

def get_characters_by_text(db: Session, text_id: int) -> List[models.Character]:
    return db.query(models.Character).filter(models.Character.text_id == text_id).all()

def update_character_voice(db: Session, character_id: int, provider_id: str, provider: str = "HUME") -> Optional[models.Character]:
    db_character = db.query(models.Character).filter(models.Character.id == character_id).first()
    if db_character:
        db_character.provider_id = provider_id
        db_character.provider = provider
        db.commit()
        db.refresh(db_character)
    return db_character

def get_character(db: Session, character_id: int) -> Optional[models.Character]:
    """Get a character by ID"""
    return db.query(models.Character).filter(models.Character.id == character_id).first()

def delete_characters_by_text(db: Session, text_id: int) -> int:
    """Delete all characters associated with a text_id
    
    Returns:
        int: Number of deleted characters
    """
    result = db.query(models.Character).filter(
        models.Character.text_id == text_id
    ).delete(synchronize_session=False)
    db.commit()
    return result

# TextSegment CRUD
def create_text_segment(
    db: Session,
    text_id: int,
    character_id: int,
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
        text_id=text_id,
        character_id=character_id,
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

def get_segments_by_text(db: Session, text_id: int) -> List[models.TextSegment]:
    return db.query(models.TextSegment).filter(
        models.TextSegment.text_id == text_id
    ).order_by(models.TextSegment.sequence).all()

def delete_segments_by_text(db: Session, text_id: int) -> int:
    """Delete all text segments associated with a text_id
    
    Returns:
        int: Number of deleted segments
    """
    result = db.query(models.TextSegment).filter(
        models.TextSegment.text_id == text_id
    ).delete(synchronize_session=False)
    db.commit()
    return result

def update_segment_audio(db: Session, segment_id: int, audio_file: str) -> Optional[models.TextSegment]:
    db_segment = db.query(models.TextSegment).filter(models.TextSegment.id == segment_id).first()
    if db_segment:
        db_segment.audio_file = audio_file
        db.commit()
        db.refresh(db_segment)
    return db_segment

def update_segment_audio_data(db: Session, segment_id: int, audio_data_b64: str) -> Optional[models.TextSegment]:
    db_segment = db.query(models.TextSegment).filter(models.TextSegment.id == segment_id).first()
    if db_segment:
        db_segment.audio_data_b64 = audio_data_b64
        db.commit()
        db.refresh(db_segment)
    return db_segment

# ProcessLog CRUD
def create_log(
    db: Session,
    operation: str,
    status: str,
    text_id: Optional[int] = None,
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

# SoundEffect CRUD
def create_sound_effect(
    db: Session,
    effect_name: str,
    text_id: int,
    start_word: str,
    end_word: str,
    prompt: str,
    audio_data_b64: str,
    segment_id: Optional[int] = None,  # Now optional
    start_word_position: Optional[int] = None,  # Position of start word in text
    end_word_position: Optional[int] = None,    # Position of end word in text
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    total_time: Optional[int] = None,
    rank: Optional[int] = None  # Importance ranking from Claude analysis (1 = most important)
) -> models.SoundEffect:
    """Create a new sound effect"""
    # Calculate total_time if start_time and end_time are provided but total_time is not
    if total_time is None and start_time is not None and end_time is not None:
        duration = end_time - start_time
        total_time = max(1, round(duration))  # Round to seconds, minimum 1 second
    
    db_sound_effect = models.SoundEffect(
        effect_name=effect_name,
        text_id=text_id,
        segment_id=segment_id,  # Can be None
        start_word=start_word,
        end_word=end_word,
        start_word_position=start_word_position,
        end_word_position=end_word_position,
        prompt=prompt,
        audio_data_b64=audio_data_b64,
        start_time=start_time,
        end_time=end_time,
        total_time=total_time,
        rank=rank
    )
    db.add(db_sound_effect)
    db.commit()
    db.refresh(db_sound_effect)
    return db_sound_effect

def get_sound_effect(db: Session, effect_id: int) -> Optional[models.SoundEffect]:
    """Get a sound effect by ID"""
    return db.query(models.SoundEffect).filter(models.SoundEffect.effect_id == effect_id).first()

def get_sound_effects_by_text(db: Session, text_id: int) -> List[models.SoundEffect]:
    """Get all sound effects for a text"""
    return db.query(models.SoundEffect).filter(models.SoundEffect.text_id == text_id).all()

def get_sound_effects_by_segment(db: Session, segment_id: int) -> List[models.SoundEffect]:
    """Get all sound effects for a text segment"""
    return db.query(models.SoundEffect).filter(models.SoundEffect.segment_id == segment_id).all()

def update_sound_effect_timing(
    db: Session, 
    effect_id: int, 
    start_time: Optional[float] = None, 
    end_time: Optional[float] = None
) -> Optional[models.SoundEffect]:
    """Update the timing information for a sound effect"""
    db_sound_effect = get_sound_effect(db, effect_id)
    if db_sound_effect:
        if start_time is not None:
            db_sound_effect.start_time = start_time
        if end_time is not None:
            db_sound_effect.end_time = end_time
        
        # Calculate and update total_time if we have both start and end times
        if db_sound_effect.start_time is not None and db_sound_effect.end_time is not None:
            duration = db_sound_effect.end_time - db_sound_effect.start_time
            db_sound_effect.total_time = max(1, round(duration))  # Round to seconds, minimum 1 second
        
        db.commit()
        db.refresh(db_sound_effect)
    return db_sound_effect

def update_sound_effect_audio(
    db: Session,
    effect_id: int,
    audio_data_b64: str,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> Optional[models.SoundEffect]:
    """Update the audio data and timing for a sound effect"""
    db_sound_effect = get_sound_effect(db, effect_id)
    if db_sound_effect:
        db_sound_effect.audio_data_b64 = audio_data_b64
        if start_time is not None:
            db_sound_effect.start_time = start_time
        if end_time is not None:
            db_sound_effect.end_time = end_time
        
        # Calculate and update total_time if we have both start and end times
        if db_sound_effect.start_time is not None and db_sound_effect.end_time is not None:
            duration = db_sound_effect.end_time - db_sound_effect.start_time
            db_sound_effect.total_time = max(1, round(duration))  # Round to seconds, minimum 1 second
        
        db.commit()
        db.refresh(db_sound_effect)
    return db_sound_effect

def delete_sound_effect(db: Session, effect_id: int) -> bool:
    """Delete a sound effect by ID"""
    db_sound_effect = get_sound_effect(db, effect_id)
    if db_sound_effect:
        db.delete(db_sound_effect)
        db.commit()
        return True
    return False

def delete_sound_effects_by_text(db: Session, text_id: int) -> int:
    """Delete all sound effects associated with a text_id
    
    Returns:
        int: Number of deleted sound effects
    """
    result = db.query(models.SoundEffect).filter(
        models.SoundEffect.text_id == text_id
    ).delete(synchronize_session=False)
    db.commit()
    return result

def delete_sound_effects_by_segment(db: Session, segment_id: int) -> int:
    """Delete all sound effects associated with a segment_id
    
    Returns:
        int: Number of deleted sound effects
    """
    result = db.query(models.SoundEffect).filter(
        models.SoundEffect.segment_id == segment_id
    ).delete(synchronize_session=False)
    db.commit()
    return result

def delete_all_sound_effects(db: Session) -> int:
    """Delete ALL sound effects from the database
    
    Returns:
        int: Number of deleted sound effects
    """
    result = db.query(models.SoundEffect).delete(synchronize_session=False)
    db.commit()
    return result