import pytest
from narratix.core.domain.entities.voice import Voice

def test_voice_initialization():
    """Test basic initialization of Voice."""
    voice_id = "polly-joanna"
    voice_name = "Joanna"
    provider = "AWS"
    gender = "Female"
    accent = "US English"
    description = "Friendly and conversational"
    pitch = 0.1
    
    voice = Voice(
        voice_id=voice_id,
        voice_name=voice_name,
        provider=provider,
        gender=gender,
        accent=accent,
        voice_description=description,
        pitch=pitch
    )
    
    assert voice.voice_id == voice_id
    assert voice.voice_name == voice_name
    assert voice.provider == provider
    assert voice.gender == gender
    assert voice.accent == accent
    assert voice.voice_description == description
    assert voice.pitch == pitch

def test_voice_initialization_minimal():
    """Test initialization with only required fields."""
    voice_id = "google-basic"
    voice_name = "Basic"
    provider = "Google"
    
    voice = Voice(voice_id=voice_id, voice_name=voice_name, provider=provider)
    
    assert voice.voice_id == voice_id
    assert voice.voice_name == voice_name
    assert voice.provider == provider
    assert voice.gender == "Neutral"  # Default gender
    assert voice.accent is None
    assert voice.voice_description is None
    assert voice.pitch == 0.0         # Default pitch 