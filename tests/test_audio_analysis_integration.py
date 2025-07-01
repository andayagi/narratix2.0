"""
Integration tests for audio_analysis.py service.
Tests the unified audio analysis workflow with mocked Anthropic API calls.
"""
import sys
import os
import json
from unittest.mock import patch, MagicMock

# Add the project root to the Python path to allow direct script execution
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from sqlalchemy.orm import Session

from db import models, crud
from services.audio_analysis import analyze_text_for_audio, process_audio_analysis_for_text
from db.database import SessionLocal, Base, engine

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Test data
TEST_TEXT_CONTENT = """The old wooden door creaked as Sarah opened it slowly. Thunder rumbled in the distance while rain pattered against the windows. She stepped into the dark hallway, her footsteps echoing on the wooden floor."""

# Longer text for comprehensive testing (over 2100 characters to allow 3 effects: 2100 // 700 = 3)
LONG_TEST_TEXT = """The old wooden door creaked ominously as Sarah opened it slowly, each ancient hinge protesting with a grinding, metallic squeal that echoed through the abandoned mansion. Thunder rumbled menacingly in the distance while heavy rain pattered insistently against the frost-covered windows, creating an irregular rhythm that seemed to mock her racing heartbeat. She stepped cautiously into the dark, foreboding hallway, her leather boots clicking and echoing hollowly on the ancient wooden floor that had witnessed decades of secrets and sorrows. The weathered floorboards groaned and complained beneath her weight, and somewhere deep in the shadowy recesses of the house, she could hear the faint, persistent dripping of water from a leaky ceiling, each drop marking time like a mournful metronome. A sudden, violent gust of wind rattled the windows with tremendous force, causing the entire old house to shudder and creak around her like a living thing in pain. The oppressive darkness seemed to press in from all sides, thick and suffocating, while the ferocious storm outside grew more violent and threatening with each passing moment. Lightning flashed briefly and brilliantly, illuminating the dusty, cobweb-filled corridor for a split second before plunging everything back into impenetrable, absolute blackness that seemed to swallow all hope and courage. The air was heavy with the scent of decay and forgotten memories, and every shadow seemed to harbor unknown terrors waiting to spring forth."""

MOCK_CLAUDE_RESPONSE = {
    "sound_effects": [
        {
            "effect_name": "wooden-door-creak",
            "description": "Old wooden door creaking open slowly",
            "start_word": "door",
            "end_word": "creaked",
            "prompt": "old wooden door creaking open slowly, horror movie style, high quality",
            "rank": "1",
            "start_word_number": "4", 
            "end_word_number": "5"
        },
        {
            "effect_name": "thunder-distant",
            "description": "Distant thunder rumbling",
            "start_word": "Thunder",
            "end_word": "rumbled",
            "prompt": "distant thunder rumbling softly, cinematic, high quality",
            "rank": "2",
            "start_word_number": "11", 
            "end_word_number": "12"
        },
        {
            "effect_name": "rain-patter",
            "description": "Rain pattering on windows",
            "start_word": "rain",
            "end_word": "windows",
            "prompt": "gentle rain pattering on glass windows, atmospheric, high quality",
            "rank": "3",
            "start_word_number": "17", 
            "end_word_number": "21"
        }
    ],
    "soundscape": "Slow, ominous percussion with deep atmospheric undertones. Rain and wind create natural ambience suggesting a horror/thriller genre, with rhythmic tension building throughout the scene."
}

@pytest.mark.integration
class TestAudioAnalysisIntegration:
    """Integration tests for audio analysis service"""
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self, db_session: Session):
        """Setup test data and cleanup after each test"""
        self.db = db_session
        
        # Create test text
        self.test_text = crud.create_text(
            db=self.db,
            content=TEST_TEXT_CONTENT,
            title="Audio Analysis Test Text"
        )
        
        yield
        
        # Cleanup: delete all sound effects and text
        self.db.query(models.SoundEffect).filter(
            models.SoundEffect.text_id == self.test_text.id
        ).delete()
        self.db.query(models.Text).filter(
            models.Text.id == self.test_text.id
        ).delete()
        self.db.commit()

    @patch('services.audio_analysis.client')
    def test_analyze_text_for_audio_success(self, mock_client):
        """Test successful unified audio analysis"""
        # Mock Anthropic API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps(MOCK_CLAUDE_RESPONSE)
        mock_client.messages.create.return_value = mock_response
        
        # Execute the function
        soundscape, sound_effects = analyze_text_for_audio(self.test_text.id)
        
        # Verify results
        assert soundscape is not None
        assert "ominous percussion" in soundscape
        assert len(sound_effects) == 3
        
        # Verify sound effects structure
        assert sound_effects[0]['effect_name'] == 'wooden-door-creak'
        assert sound_effects[0]['start_word_number'] == 4
        assert sound_effects[0]['end_word_number'] == 5
        
        assert sound_effects[1]['effect_name'] == 'thunder-distant'
        assert sound_effects[2]['effect_name'] == 'rain-patter'
        
        # Verify API was called with correct parameters
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        assert call_args[1]['model'] == 'claude-3-5-haiku-20241022'
        assert call_args[1]['max_tokens'] > 3000  # Dynamic calculation, should be reasonable
        assert call_args[1]['temperature'] == 0

    @patch('services.audio_analysis.client')
    def test_analyze_text_for_audio_malformed_response(self, mock_client):
        """Test handling of malformed Claude response"""
        # Mock malformed response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "This is not valid JSON content"
        mock_client.messages.create.return_value = mock_response
        
        # Execute the function
        soundscape, sound_effects = analyze_text_for_audio(self.test_text.id)
        
        # Verify error handling
        assert soundscape is None
        assert sound_effects == []

    @patch('services.audio_analysis.client')
    def test_analyze_text_for_audio_api_error(self, mock_client):
        """Test handling of Anthropic API error"""
        # Mock API error
        mock_client.messages.create.side_effect = Exception("API Error")
        
        # Execute the function
        soundscape, sound_effects = analyze_text_for_audio(self.test_text.id)
        
        # Verify error handling
        assert soundscape is None
        assert sound_effects == []

    def test_analyze_text_for_audio_nonexistent_text(self):
        """Test handling of non-existent text ID"""
        # Use non-existent text ID
        soundscape, sound_effects = analyze_text_for_audio(99999)
        
        # Verify error handling
        assert soundscape is None
        assert sound_effects == []

    @patch('services.audio_analysis.client')
    def test_process_audio_analysis_for_text_success(self, mock_client):
        """Test complete end-to-end audio analysis processing"""
        # Mock Anthropic API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps(MOCK_CLAUDE_RESPONSE)
        mock_client.messages.create.return_value = mock_response
        
        # Execute the function
        success, soundscape, sound_effects = process_audio_analysis_for_text(
            self.test_text.id
        )
        
        # Verify success
        assert success is True
        assert soundscape is not None
        # Note: Text length filtering may reduce the number of effects
        assert len(sound_effects) >= 1
        
        # Verify soundscape was stored in database
        self.db.refresh(self.test_text)
        assert self.test_text.background_music_prompt == soundscape
        
        # Verify sound effects were stored in database
        db_sound_effects = crud.get_sound_effects_by_text(self.db, self.test_text.id)
        assert len(db_sound_effects) >= 1
        
        # Verify the highest ranked effect was stored (due to text length filtering)
        door_effect = next(se for se in db_sound_effects if se.effect_name == 'wooden-door-creak')
        assert door_effect.start_word == 'door'
        assert door_effect.end_word == 'creaked'
        assert door_effect.start_word_position == 4
        assert door_effect.end_word_position == 5
        assert door_effect.rank == 1
        assert door_effect.total_time == 2  # (5-4+1) = 2 words = 2 seconds

    @patch('services.audio_analysis.client')
    def test_process_audio_analysis_text_length_filtering(self, mock_client):
        """Test that sound effects are filtered based on text length"""
        # Create a short text (less than 700 characters)
        short_text = crud.create_text(
            db=self.db,
            content="Short text with door creaking.",
            title="Short Text"
        )
        
        # Mock response with multiple effects
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps(MOCK_CLAUDE_RESPONSE)
        mock_client.messages.create.return_value = mock_response
        
        try:
            # Execute the function
            success, soundscape, sound_effects = process_audio_analysis_for_text(
                short_text.id
            )
            
            # Verify success
            assert success is True
            
            # For short text (< 700 chars), should only keep 1 effect (max(1, 30//700) = 1)
            db_sound_effects = crud.get_sound_effects_by_text(self.db, short_text.id)
            assert len(db_sound_effects) == 1
            
            # Should keep the highest ranked effect (rank 1)
            assert db_sound_effects[0].effect_name == 'wooden-door-creak'
            assert db_sound_effects[0].rank == 1
            
        finally:
            # Cleanup
            self.db.query(models.SoundEffect).filter(
                models.SoundEffect.text_id == short_text.id
            ).delete()
            self.db.query(models.Text).filter(
                models.Text.id == short_text.id
            ).delete()
            self.db.commit()

    @patch('services.audio_analysis.client')
    def test_process_audio_analysis_for_long_text_success(self, mock_client):
        """Test complete end-to-end audio analysis processing with longer text"""
        # Create a longer text to allow multiple sound effects
        long_text = crud.create_text(
            db=self.db,
            content=LONG_TEST_TEXT,
            title="Long Audio Analysis Test Text"
        )
        
        # Mock Anthropic API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps(MOCK_CLAUDE_RESPONSE)
        mock_client.messages.create.return_value = mock_response
        
        try:
            # Execute the function
            success, soundscape, sound_effects = process_audio_analysis_for_text(
                long_text.id
            )
            
            # Verify success
            assert success is True
            assert soundscape is not None
            assert len(sound_effects) == 3  # Long text should allow all 3 effects
            
            # Verify soundscape was stored in database
            self.db.refresh(long_text)
            assert long_text.background_music_prompt == soundscape
            
            # Verify all sound effects were stored in database
            db_sound_effects = crud.get_sound_effects_by_text(self.db, long_text.id)
            assert len(db_sound_effects) == 3
            
            # Verify sound effect details
            door_effect = next(se for se in db_sound_effects if se.effect_name == 'wooden-door-creak')
            assert door_effect.start_word == 'door'
            assert door_effect.end_word == 'creaked'
            assert door_effect.rank == 1
            
            thunder_effect = next(se for se in db_sound_effects if se.effect_name == 'thunder-distant')
            assert thunder_effect.rank == 2
            
            rain_effect = next(se for se in db_sound_effects if se.effect_name == 'rain-patter')
            assert rain_effect.rank == 3
            
        finally:
            # Cleanup
            self.db.query(models.SoundEffect).filter(
                models.SoundEffect.text_id == long_text.id
            ).delete()
            self.db.query(models.Text).filter(
                models.Text.id == long_text.id
            ).delete()
            self.db.commit()

    @patch('services.audio_analysis.client')
    def test_process_audio_analysis_rank_sorting(self, mock_client):
        """Test that sound effects are properly sorted by rank"""
        # Mock response with unordered ranks
        unordered_response = {
            "sound_effects": [
                {
                    "effect_name": "effect-rank-3",
                    "start_word": "word1",
                    "end_word": "word1",
                    "prompt": "test effect 3",
                    "rank": "3",
                    "start_word_number": "1",
                    "end_word_number": "1"
                },
                {
                    "effect_name": "effect-rank-1",
                    "start_word": "word2",
                    "end_word": "word2",
                    "prompt": "test effect 1",
                    "rank": "1",
                    "start_word_number": "2",
                    "end_word_number": "2"
                },
                {
                    "effect_name": "effect-rank-2",
                    "start_word": "word3",
                    "end_word": "word3",
                    "prompt": "test effect 2",
                    "rank": "2",
                    "start_word_number": "3",
                    "end_word_number": "3"
                }
            ],
            "soundscape": "Test soundscape"
        }
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps(unordered_response)
        mock_client.messages.create.return_value = mock_response
        
        # Execute the function
        success, soundscape, sound_effects = process_audio_analysis_for_text(
            self.test_text.id
        )
        
        # Verify success
        assert success is True
        
        # Verify effects are sorted by rank (text length filtering may reduce count)
        assert len(sound_effects) >= 1
        assert sound_effects[0]['effect_name'] == 'effect-rank-1'  # Best rank should be first

    @patch('services.audio_analysis.client')
    def test_process_audio_analysis_invalid_word_numbers(self, mock_client):
        """Test handling of invalid word numbers in Claude response"""
        # Mock response with invalid word numbers
        invalid_response = {
            "sound_effects": [
                {
                    "effect_name": "test-effect",
                    "start_word": "word",
                    "end_word": "word",
                    "prompt": "test effect",
                    "rank": "1",
                    "start_word_number": "invalid",
                    "end_word_number": "also_invalid"
                }
            ],
            "soundscape": "Test soundscape"
        }
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps(invalid_response)
        mock_client.messages.create.return_value = mock_response
        
        # Execute the function
        success, soundscape, sound_effects = process_audio_analysis_for_text(
            self.test_text.id
        )
        
        # Verify success (should still work with default values)
        assert success is True
        
        # Verify effect was stored with None word positions
        db_sound_effects = crud.get_sound_effects_by_text(self.db, self.test_text.id)
        assert len(db_sound_effects) == 1
        assert db_sound_effects[0].start_word_position is None
        assert db_sound_effects[0].end_word_position is None
        assert db_sound_effects[0].total_time == 2  # Default value

    def test_word_placement_generation(self):
        """Test that word placement data is correctly generated"""
        # This is tested indirectly through the API call, but we can verify
        # the text processing works correctly
        words = TEST_TEXT_CONTENT.split()
        
        # Verify we have the expected words
        assert words[3] == "door"  # Should be at position 4 (1-indexed)
        assert words[4] == "creaked"  # Should be at position 5 (1-indexed)
        assert words[10] == "Thunder"  # Should be at position 11 (1-indexed)
        
        # Test word cleaning (punctuation removal)
        test_word = "windows."
        clean_word = test_word.strip('.,!?;:"()[]{}').lower()
        assert clean_word == "windows"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 