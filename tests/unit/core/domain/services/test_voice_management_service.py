"""
Tests for the VoiceManagementService protocol.
"""
import unittest
from typing import List, Dict, Any, Optional, Protocol, runtime_checkable

from src.narratix.core.domain.entities.voice import Voice
from src.narratix.core.domain.entities.character import Character
from src.narratix.core.domain.services.voice_management_service import VoiceManagementService


class MockVoiceManagementService:
    """Mock implementation of VoiceManagementService for testing."""
    
    def __init__(self):
        """Initialize with some test voices."""
        self.voices = {
            "voice-1": Voice(
                voice_id="voice-1", 
                voice_name="Male Adult", 
                provider="AWS", 
                gender="Male", 
                accent="US English"
            ),
            "voice-2": Voice(
                voice_id="voice-2", 
                voice_name="Female Adult", 
                provider="AWS", 
                gender="Female", 
                accent="British English"
            ),
            "voice-3": Voice(
                voice_id="voice-3", 
                voice_name="Child Voice", 
                provider="ElevenLabs", 
                gender="Neutral", 
                accent="US English"
            )
        }
        self.character_voices = {}
    
    def get_available_voices(self) -> List[Voice]:
        return list(self.voices.values())
    
    def get_voice_by_id(self, voice_id: str) -> Optional[Voice]:
        return self.voices.get(voice_id)
    
    def filter_voices(self, criteria: Dict[str, Any]) -> List[Voice]:
        results = []
        for voice in self.voices.values():
            match = True
            for key, value in criteria.items():
                # Adjust attribute names to match Voice class attributes
                if key == "gender" and getattr(voice, key) != value:
                    match = False
                    break
                if key == "accent" and getattr(voice, key) != value:
                    match = False
                    break
            if match:
                results.append(voice)
        return results
    
    def assign_voice_to_character(self, character: Character, voice: Voice) -> bool:
        character.assign_voice(voice)
        return True
    
    def create_custom_voice(self, voice_data: Dict[str, Any]) -> Voice:
        voice_id = voice_data.get("voice_id", f"voice-{len(self.voices) + 1}")
        # Ensure we have the required parameters
        if "voice_name" not in voice_data:
            voice_data["voice_name"] = "Custom Voice"
        if "provider" not in voice_data:
            voice_data["provider"] = "Custom"
            
        voice = Voice(
            voice_id=voice_id,
            voice_name=voice_data["voice_name"],
            provider=voice_data["provider"],
            gender=voice_data.get("gender", "Neutral"),
            accent=voice_data.get("accent", None),
            voice_description=voice_data.get("voice_description", None),
            pitch=voice_data.get("pitch", 0.0)
        )
        self.voices[voice_id] = voice
        return voice
    
    def update_voice(self, voice_id: str, voice_data: Dict[str, Any]) -> Optional[Voice]:
        if voice_id not in self.voices:
            return None
        
        voice = self.voices[voice_id]
        # Map the voice_data keys to the appropriate attributes
        if "voice_name" in voice_data:
            voice.voice_name = voice_data["voice_name"]
        if "gender" in voice_data:
            voice.gender = voice_data["gender"]
        if "accent" in voice_data:
            voice.accent = voice_data["accent"]
        if "voice_description" in voice_data:
            voice.voice_description = voice_data["voice_description"]
        if "pitch" in voice_data:
            voice.pitch = voice_data["pitch"]
        
        return voice


class TestVoiceManagementService(unittest.TestCase):
    """Tests for the VoiceManagementService protocol."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = MockVoiceManagementService()
        # Create a simple Character for testing
        self.sample_character = Character(
            name="Alice",
            description="Main character"
        )
    
    def test_protocol_conformance(self):
        """Test that our mock correctly implements the protocol."""
        # Since Protocol classes don't have a direct way to check conformance in runtime,
        # we'll just check that the service has all the required methods
        self.assertTrue(hasattr(self.mock_service, "get_available_voices"))
        self.assertTrue(hasattr(self.mock_service, "get_voice_by_id"))
        self.assertTrue(hasattr(self.mock_service, "filter_voices"))
        self.assertTrue(hasattr(self.mock_service, "assign_voice_to_character"))
        self.assertTrue(hasattr(self.mock_service, "create_custom_voice"))
        self.assertTrue(hasattr(self.mock_service, "update_voice"))
    
    def test_get_available_voices(self):
        """Test the get_available_voices method."""
        voices = self.mock_service.get_available_voices()
        self.assertIsInstance(voices, list)
        self.assertEqual(len(voices), 3)
        self.assertIsInstance(voices[0], Voice)
    
    def test_get_voice_by_id(self):
        """Test the get_voice_by_id method."""
        voice = self.mock_service.get_voice_by_id("voice-1")
        self.assertIsInstance(voice, Voice)
        self.assertEqual(voice.voice_id, "voice-1")
        
        # Test non-existent voice
        non_existent = self.mock_service.get_voice_by_id("non-existent")
        self.assertIsNone(non_existent)
    
    def test_filter_voices(self):
        """Test the filter_voices method."""
        # Filter by gender
        female_voices = self.mock_service.filter_voices({"gender": "Female"})
        self.assertEqual(len(female_voices), 1)
        self.assertEqual(female_voices[0].gender, "Female")
        
        # Filter by accent
        british_voices = self.mock_service.filter_voices({"accent": "British English"})
        self.assertEqual(len(british_voices), 1)
        self.assertEqual(british_voices[0].accent, "British English")
    
    def test_assign_voice_to_character(self):
        """Test the assign_voice_to_character method."""
        voice = self.mock_service.get_voice_by_id("voice-2")
        result = self.mock_service.assign_voice_to_character(
            self.sample_character, voice
        )
        self.assertTrue(result)
        self.assertEqual(self.sample_character.voice, voice)
    
    def test_create_custom_voice(self):
        """Test the create_custom_voice method."""
        voice_data = {
            "voice_name": "Custom Voice",
            "provider": "Custom",
            "gender": "Female",
            "accent": "British English",
            "voice_description": "Elderly British woman"
        }
        voice = self.mock_service.create_custom_voice(voice_data)
        self.assertIsInstance(voice, Voice)
        self.assertEqual(voice.voice_name, "Custom Voice")
        self.assertEqual(voice.gender, "Female")
        self.assertEqual(voice.accent, "British English")
        
        # Verify it was added to the available voices
        voices = self.mock_service.get_available_voices()
        self.assertEqual(len(voices), 4)
    
    def test_update_voice(self):
        """Test the update_voice method."""
        updates = {"voice_name": "Updated Voice", "accent": "Scottish"}
        updated_voice = self.mock_service.update_voice("voice-1", updates)
        
        self.assertIsInstance(updated_voice, Voice)
        self.assertEqual(updated_voice.voice_name, "Updated Voice")
        self.assertEqual(updated_voice.accent, "Scottish")
        
        # Test updating non-existent voice
        non_existent = self.mock_service.update_voice("non-existent", updates)
        self.assertIsNone(non_existent)


if __name__ == "__main__":
    unittest.main() 