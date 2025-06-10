from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Base SoundEffect schemas
class SoundEffectBase(BaseModel):
    effect_name: str
    text_id: int
    start_word: str
    end_word: str
    prompt: str
    segment_id: Optional[int] = None
    start_word_position: Optional[int] = None
    end_word_position: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    rank: Optional[int] = None  # Importance ranking from Claude analysis (1 = most important)

class SoundEffectCreate(SoundEffectBase):
    audio_data_b64: str

class SoundEffect(SoundEffectBase):
    effect_id: int
    audio_data_b64: str
    created_at: datetime

    class Config:
        from_attributes = True 