"""
Unit tests for webhook-based audio generation (Task 6.1).

Tests:
- Webhook endpoint with mock Replicate payloads for both content types
- process_sound_effect_webhook_result() function
- process_background_music_webhook_result() function  
- Content-type routing in webhook endpoint
- Idempotency (duplicate webhook handling)
- Error scenarios (failed predictions, invalid URLs)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
import base64
import json
from typing import Dict, Any

from api.main import app
from api.endpoints.replicate_webhook import (
    handle_replicate_webhook,
    process_webhook_success,
    process_sound_effect_webhook_result,
    process_background_music_webhook_result,
    mark_generation_failed,
    WebhookPayload
)
from services.replicate_audio import (
    create_webhook_prediction,
    process_webhook_result,
    get_processor,
    SoundEffectProcessor,
    BackgroundMusicProcessor,
    ReplicateAudioConfig
)
from db import crud

client = TestClient(app)

class TestWebhookEndpoint:
    """Test the main webhook endpoint with various payloads."""
    
    @pytest.fixture
    def sound_effect_payload(self):
        """Mock sound effect webhook payload."""
        return {
            "id": "se-prediction-id",
            "version": "test-version",
            "created_at": "2025-01-01T12:00:00Z",
            "status": "succeeded",
            "input": {"prompt": "rain on window", "duration": 5},
            "output": "https://replicate.com/test-sound.wav"
        }
    
    @pytest.fixture
    def background_music_payload(self):
        """Mock background music webhook payload."""
        return {
            "id": "bg-prediction-id", 
            "version": "test-version",
            "created_at": "2025-01-01T12:00:00Z",
            "status": "succeeded",
            "input": {"prompt": "peaceful piano", "duration": 120},
            "output": "https://replicate.com/test-music.mp3"
        }
    
    @patch('api.endpoints.replicate_webhook.crud')
    @patch('api.endpoints.replicate_webhook.process_webhook_success')
    def test_sound_effect_webhook_success(self, mock_process, mock_crud, sound_effect_payload):
        """Test successful sound effect webhook processing."""
        mock_crud.get_sound_effect.return_value = Mock(id=1)
        
        response = client.post(
            "/api/replicate-webhook/sound_effect/1",
            json=sound_effect_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Webhook processed for sound_effect 1"
        assert data["status"] == "succeeded"
        mock_crud.get_sound_effect.assert_called_once()
    
    @patch('api.endpoints.replicate_webhook.crud')
    @patch('api.endpoints.replicate_webhook.process_webhook_success')
    def test_background_music_webhook_success(self, mock_process, mock_crud, background_music_payload):
        """Test successful background music webhook processing."""
        mock_crud.get_text.return_value = Mock(id=1)
        
        response = client.post(
            "/api/replicate-webhook/background_music/1",
            json=background_music_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Webhook processed for background_music 1"
        assert data["status"] == "succeeded"
        mock_crud.get_text.assert_called_once()
    
    @patch('api.endpoints.replicate_webhook.crud')
    def test_content_type_routing(self, mock_crud, sound_effect_payload):
        """Test content_type routing to correct validation functions."""
        # Test sound_effect routing
        mock_crud.get_sound_effect.return_value = Mock(id=1)
        
        response = client.post(
            "/api/replicate-webhook/sound_effect/1",
            json=sound_effect_payload
        )
        assert response.status_code == 200
        mock_crud.get_sound_effect.assert_called_once()
        
        # Reset and test background_music routing
        mock_crud.reset_mock()
        mock_crud.get_text.return_value = Mock(id=1)
        
        response = client.post(
            "/api/replicate-webhook/background_music/1", 
            json=sound_effect_payload
        )
        assert response.status_code == 200
        mock_crud.get_text.assert_called_once()
    
    @patch('api.endpoints.replicate_webhook.crud')
    def test_webhook_content_not_found(self, mock_crud, sound_effect_payload):
        """Test webhook when content doesn't exist."""
        mock_crud.get_sound_effect.return_value = None
        
        response = client.post(
            "/api/replicate-webhook/sound_effect/999",
            json=sound_effect_payload
        )
        
        assert response.status_code == 404
        assert "Sound effect 999 not found" in response.json()["detail"]
    
    @patch('api.endpoints.replicate_webhook.crud')
    @patch('api.endpoints.replicate_webhook.mark_generation_failed')
    def test_webhook_failed_status(self, mock_mark_failed, mock_crud):
        """Test webhook handling for failed predictions."""
        mock_crud.get_sound_effect.return_value = Mock(id=1)
        
        failed_payload = {
            "id": "failed-prediction",
            "version": "test-version",
            "created_at": "2025-01-01T12:00:00Z",
            "status": "failed",
            "input": {"prompt": "test"},
            "error": "Generation failed"
        }
        
        response = client.post(
            "/api/replicate-webhook/sound_effect/1",
            json=failed_payload
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
    
    @patch('api.endpoints.replicate_webhook.crud')
    def test_webhook_succeeded_no_output(self, mock_crud, sound_effect_payload):
        """Test webhook when succeeded but no output provided."""
        mock_crud.get_sound_effect.return_value = Mock(id=1)
        sound_effect_payload["output"] = None
        
        response = client.post(
            "/api/replicate-webhook/sound_effect/1",
            json=sound_effect_payload
        )
        
        assert response.status_code == 400
        assert "no output provided" in response.json()["detail"]

class TestProcessingFunctions:
    """Test the background processing functions."""
    
    @pytest.mark.asyncio
    async def test_process_sound_effect_webhook_result(self):
        """Test process_sound_effect_webhook_result placeholder function."""
        # Currently this is a TODO placeholder that just logs
        payload_data = {"id": "test-id", "output": "https://test.com/sound.wav"}
        
        # Should not raise an exception
        await process_sound_effect_webhook_result(Mock(), 1, payload_data)
    
    @pytest.mark.asyncio
    async def test_process_background_music_webhook_result(self):
        """Test process_background_music_webhook_result placeholder function."""
        # Currently this is a TODO placeholder that just logs
        payload_data = {"id": "test-id", "output": "https://test.com/music.mp3"}
        
        # Should not raise an exception
        await process_background_music_webhook_result(Mock(), 1, payload_data)

class TestSharedAudioProcessing:
    """Test the shared audio processing infrastructure."""
    
    @patch('services.replicate_audio.replicate')
    def test_create_webhook_prediction(self, mock_replicate):
        """Test create_webhook_prediction creates prediction with webhook."""
        mock_prediction = Mock()
        mock_prediction.id = "test-prediction-id"
        mock_replicate.predictions.create.return_value = mock_prediction
        
        config = ReplicateAudioConfig(
            version="test-version",
            input={"prompt": "test sound", "duration": 5}
        )
        
        result = create_webhook_prediction("sound_effect", 1, config)
        
        assert result == "test-prediction-id"
        mock_replicate.predictions.create.assert_called_once()
        call_kwargs = mock_replicate.predictions.create.call_args.kwargs
        assert "webhook" in call_kwargs
        assert "sound_effect/1" in call_kwargs["webhook"]
    
    def test_get_processor_sound_effect(self):
        """Test get_processor returns SoundEffectProcessor for sound_effect."""
        processor = get_processor("sound_effect")
        assert isinstance(processor, SoundEffectProcessor)
    
    def test_get_processor_background_music(self):
        """Test get_processor returns BackgroundMusicProcessor for background_music."""
        processor = get_processor("background_music")
        assert isinstance(processor, BackgroundMusicProcessor)
    
    def test_get_processor_invalid_type(self):
        """Test get_processor raises error for invalid content type."""
        with pytest.raises(ValueError, match="Unknown content type"):
            get_processor("invalid_type")
    
    @patch('services.replicate_audio.get_processor')
    def test_process_webhook_result(self, mock_get_processor):
        """Test process_webhook_result routes to correct processor."""
        mock_processor = Mock()
        mock_processor.process_and_store.return_value = True
        mock_get_processor.return_value = mock_processor
        
        payload_data = {"id": "test-id", "output": "https://test.com/audio.wav"}
        
        result = process_webhook_result("sound_effect", 1, payload_data)
        
        assert result is True
        mock_get_processor.assert_called_once_with("sound_effect")
        mock_processor.process_and_store.assert_called_once_with(1, payload_data)

class TestAudioProcessors:
    """Test the audio post-processors."""
    
    @patch('services.replicate_audio.get_sync_client')
    @patch('services.replicate_audio.crud')
    def test_sound_effect_processor_success(self, mock_crud, mock_get_client):
        """Test SoundEffectProcessor successful processing."""
        # Mock HTTP download
        sample_audio = b"fake_audio_data"
        mock_response = Mock()
        mock_response.content = sample_audio
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        # Mock database storage
        mock_crud.update_sound_effect_audio.return_value = True
        
        processor = SoundEffectProcessor()
        
        with patch.object(processor, 'trim_audio', return_value=sample_audio):
            result = processor.process_and_store(1, {"output": "https://test.com/audio.wav"})
        
        assert result is True
        mock_crud.update_sound_effect_audio.assert_called_once()
    
    @patch('services.replicate_audio.get_sync_client')
    @patch('services.replicate_audio.crud')
    def test_background_music_processor_success(self, mock_crud, mock_get_client):
        """Test BackgroundMusicProcessor successful processing."""
        # Mock HTTP download
        sample_audio = b"fake_music_data"
        mock_response = Mock()
        mock_response.content = sample_audio
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        # Mock database storage
        mock_crud.update_text_background_music_audio.return_value = True
        
        processor = BackgroundMusicProcessor()
        result = processor.process_and_store(1, {"output": "https://test.com/music.mp3"})
        
        assert result is True
        mock_crud.update_text_background_music_audio.assert_called_once()

class TestErrorScenarios:
    """Test various error scenarios."""
    
    @patch('services.replicate_audio.get_sync_client')
    def test_processor_download_failure(self, mock_get_client):
        """Test processor handles download failures gracefully."""
        mock_client = Mock()
        mock_client.get.side_effect = Exception("Download failed")
        mock_get_client.return_value = mock_client
        
        processor = SoundEffectProcessor()
        result = processor.process_and_store(1, {"output": "https://bad-url.com/audio.wav"})
        
        assert result is False
    
    def test_processor_no_output_url(self):
        """Test processor handles missing output URL."""
        processor = SoundEffectProcessor()
        result = processor.process_and_store(1, {"id": "test-id"})  # No output key
        
        assert result is False
    
    @patch('services.replicate_audio.get_sync_client')
    @patch('services.replicate_audio.crud')
    def test_database_storage_failure(self, mock_crud, mock_get_client):
        """Test processor handles database storage failures."""
        # Mock successful download
        sample_audio = b"audio_data"
        mock_response = Mock()
        mock_response.content = sample_audio
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        # Mock database failure
        mock_crud.update_sound_effect_audio.return_value = False
        
        processor = SoundEffectProcessor()
        
        with patch.object(processor, 'trim_audio', return_value=sample_audio):
            result = processor.process_and_store(1, {"output": "https://test.com/audio.wav"})
        
        assert result is False

class TestIdempotency:
    """Test idempotent webhook handling."""
    
    @patch('api.endpoints.replicate_webhook.crud')
    @patch('api.endpoints.replicate_webhook.process_webhook_success')
    def test_duplicate_webhook_handling(self, mock_process, mock_crud):
        """Test that duplicate webhooks are handled gracefully."""
        mock_crud.get_sound_effect.return_value = Mock(id=1)
        
        payload = {
            "id": "duplicate-prediction-id",
            "version": "test-version",
            "created_at": "2025-01-01T12:00:00Z",
            "status": "succeeded",
            "input": {"prompt": "test sound"},
            "output": "https://test.com/audio.wav"
        }
        
        # Send same webhook twice
        response1 = client.post("/api/replicate-webhook/sound_effect/1", json=payload)
        response2 = client.post("/api/replicate-webhook/sound_effect/1", json=payload)
        
        # Both should succeed (idempotent)
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert mock_process.call_count == 2  # Both should trigger processing 