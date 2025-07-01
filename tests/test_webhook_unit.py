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
import pytest_asyncio

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
    ReplicateAudioConfig,
    WebhookCompletionNotifier,
    WebhookNotifierFactory,
    wait_for_webhook_completion_event,
    wait_for_sound_effects_completion_event,
    AudioPostProcessor
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
    @pytest.mark.asyncio
    async def test_process_webhook_result(self, mock_get_processor):
        """Test process_webhook_result routes to correct processor."""
        mock_processor = Mock()
        # Mock async method
        async def mock_process_and_store(*args, **kwargs):
            return True
        mock_processor.process_and_store = mock_process_and_store
        mock_get_processor.return_value = mock_processor
        
        payload_data = {"id": "test-id", "output": "https://test.com/audio.wav"}
        
        # Mock database session since we're calling async version
        with patch('services.replicate_audio.managed_db_session'):
            result = await process_webhook_result("sound_effect", 1, payload_data)
        
        assert result is True
        mock_get_processor.assert_called_once_with("sound_effect")

class TestAudioProcessors:
    """Test the audio post-processors."""
    
    @patch('services.replicate_audio.get_async_client')
    @patch('services.replicate_audio.DatabaseSessionManager')
    @pytest.mark.asyncio
    async def test_sound_effect_processor_success(self, mock_db_manager, mock_get_client):
        """Test SoundEffectProcessor successful processing."""
        # Mock HTTP download
        sample_audio = b"fake_audio_data"
        mock_response = Mock()
        mock_response.content = sample_audio
        mock_client = Mock()
        
        # Mock async get method
        async def mock_get(*args, **kwargs):
            return mock_response
        mock_client.get = mock_get
        mock_get_client.return_value = mock_client
        
        # Mock database storage
        mock_db_manager.safe_execute.return_value = True
        
        processor = SoundEffectProcessor()
        mock_db = Mock()
        
        with patch.object(processor, 'trim_audio', return_value=sample_audio):
            result = await processor.process_and_store(mock_db, 1, {"output": "https://test.com/audio.wav"})
        
        assert result is True
        mock_db_manager.safe_execute.assert_called()
    
    @patch('services.replicate_audio.get_async_client')
    @patch('services.replicate_audio.DatabaseSessionManager')
    @pytest.mark.asyncio
    async def test_background_music_processor_success(self, mock_db_manager, mock_get_client):
        """Test BackgroundMusicProcessor successful processing."""
        # Mock HTTP download
        sample_audio = b"fake_music_data"
        mock_response = Mock()
        mock_response.content = sample_audio
        mock_client = Mock()
        
        # Mock async get method
        async def mock_get(*args, **kwargs):
            return mock_response
        mock_client.get = mock_get
        mock_get_client.return_value = mock_client
        
        # Mock database storage
        mock_db_manager.safe_execute.return_value = True
        
        processor = BackgroundMusicProcessor()
        mock_db = Mock()
        result = await processor.process_and_store(mock_db, 1, {"output": "https://test.com/music.mp3"})
        
        assert result is True
        mock_db_manager.safe_execute.assert_called()

class TestErrorScenarios:
    """Test various error scenarios."""
    
    @patch('services.replicate_audio.get_async_client')
    @pytest.mark.asyncio
    async def test_processor_download_failure(self, mock_get_client):
        """Test processor handles download failures gracefully."""
        mock_client = Mock()
        
        # Mock async get method that raises exception
        async def mock_get(*args, **kwargs):
            raise Exception("Download failed")
        mock_client.get = mock_get
        mock_get_client.return_value = mock_client
        
        processor = SoundEffectProcessor()
        mock_db = Mock()
        result = await processor.process_and_store(mock_db, 1, {"output": "https://bad-url.com/audio.wav"})
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_processor_no_output_url(self):
        """Test processor handles missing output URL."""
        processor = SoundEffectProcessor()
        mock_db = Mock()
        result = await processor.process_and_store(mock_db, 1, {"id": "test-id"})  # No output key
        
        assert result is False
    
    @patch('services.replicate_audio.get_async_client')
    @patch('services.replicate_audio.DatabaseSessionManager')
    @pytest.mark.asyncio
    async def test_database_storage_failure(self, mock_db_manager, mock_get_client):
        """Test processor handles database storage failures."""
        # Mock successful download
        sample_audio = b"audio_data"
        mock_response = Mock()
        mock_response.content = sample_audio
        mock_client = Mock()
        
        # Mock async get method
        async def mock_get(*args, **kwargs):
            return mock_response
        mock_client.get = mock_get
        mock_get_client.return_value = mock_client
        
        # Mock database failure
        mock_db_manager.safe_execute.return_value = False
        
        processor = SoundEffectProcessor()
        mock_db = Mock()
        
        with patch.object(processor, 'trim_audio', return_value=sample_audio):
            result = await processor.process_and_store(mock_db, 1, {"output": "https://test.com/audio.wav"})
        
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

class TestWebhookNotifierFactory:
    """Test WebhookNotifierFactory and dependency injection patterns."""
    
    def test_create_notifier_creates_new_instance(self):
        """Test that create_notifier returns new instances."""
        notifier1 = WebhookNotifierFactory.create_notifier()
        notifier2 = WebhookNotifierFactory.create_notifier()
        
        assert isinstance(notifier1, WebhookCompletionNotifier)
        assert isinstance(notifier2, WebhookCompletionNotifier)
        assert notifier1 is not notifier2  # Different instances
    
    def test_get_global_notifier_returns_same_instance(self):
        """Test that get_global_notifier returns the same instance."""
        notifier1 = WebhookNotifierFactory.get_global_notifier()
        notifier2 = WebhookNotifierFactory.get_global_notifier()
        
        assert isinstance(notifier1, WebhookCompletionNotifier)
        assert notifier1 is notifier2  # Same instance
    
    @pytest.mark.asyncio
    async def test_isolated_notifier_instances(self):
        """Test that isolated notifier instances don't interfere."""
        notifier1 = WebhookNotifierFactory.create_notifier()
        notifier2 = WebhookNotifierFactory.create_notifier()
        
        # Create events in both notifiers
        event1 = await notifier1.create_completion_event("sound_effect", 1)
        event2 = await notifier2.create_completion_event("sound_effect", 1)
        
        # Notify completion in first notifier
        await notifier1.notify_completion("sound_effect", 1, True)
        
        # Check that only first notifier's event is set
        assert event1.is_set()
        assert not event2.is_set()
        
        # Clean up
        notifier1.cleanup_event("sound_effect", 1)
        notifier2.cleanup_event("sound_effect", 1)

class TestDependencyInjection:
    """Test dependency injection for webhook processing functions."""
    
    @pytest.mark.asyncio
    async def test_process_webhook_result_with_custom_notifier(self):
        """Test process_webhook_result with custom notifier."""
        custom_notifier = WebhookNotifierFactory.create_notifier()
        
        with patch('services.replicate_audio.get_processor') as mock_get_processor:
            mock_processor = Mock(spec=AudioPostProcessor)
            mock_processor.process_and_store = AsyncMock(return_value=True)
            mock_get_processor.return_value = mock_processor
            
            # Mock notifier methods
            custom_notifier.notify_completion = AsyncMock()
            
            payload_data = {"output": "http://example.com/audio.mp3"}
            
            result = await process_webhook_result(
                "sound_effect", 1, payload_data, notifier=custom_notifier
            )
            
            assert result is True
            custom_notifier.notify_completion.assert_called_once_with("sound_effect", 1, True)
    
    @pytest.mark.asyncio
    async def test_wait_for_webhook_completion_with_custom_notifier(self):
        """Test wait_for_webhook_completion_event with custom notifier."""
        custom_notifier = WebhookNotifierFactory.create_notifier()
        
        # Mock notifier methods
        custom_notifier.create_completion_event = AsyncMock()
        custom_notifier.wait_for_completion = AsyncMock(return_value=(True, 2.5))
        custom_notifier.cleanup_event = Mock()
        
        result = await wait_for_webhook_completion_event(
            "sound_effect", 1, timeout=30, notifier=custom_notifier
        )
        
        assert result is True
        custom_notifier.create_completion_event.assert_called_once_with("sound_effect", 1)
        custom_notifier.wait_for_completion.assert_called_once_with("sound_effect", 1, 30)
        custom_notifier.cleanup_event.assert_called_once_with("sound_effect", 1)
    
    @pytest.mark.asyncio
    async def test_functions_use_global_notifier_when_none_provided(self):
        """Test that functions use global notifier when none is provided."""
        with patch.object(WebhookNotifierFactory, 'get_global_notifier') as mock_global:
            mock_notifier = Mock(spec=WebhookCompletionNotifier)
            mock_notifier.create_completion_event = AsyncMock()
            mock_notifier.wait_for_completion = AsyncMock(return_value=(True, 1.0))
            mock_notifier.cleanup_event = Mock()
            mock_global.return_value = mock_notifier
            
            # Test without passing notifier parameter
            result = await wait_for_webhook_completion_event("sound_effect", 1, timeout=30)
            
            mock_global.assert_called_once()
            assert result is True 