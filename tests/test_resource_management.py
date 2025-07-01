"""
Test file for resource management improvements in replicate_audio.py
"""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from services.replicate_audio import managed_temp_files, run_ffmpeg_safely


def test_managed_temp_files_creates_and_cleans_up():
    """Test that context manager creates files and cleans them up."""
    created_files = []
    
    with managed_temp_files('.mp3', '.wav') as (file1, file2):
        created_files = [file1, file2]
        
        # Files should exist during context
        assert os.path.exists(file1)
        assert os.path.exists(file2)
        assert file1.endswith('.mp3')
        assert file2.endswith('.wav')
    
    # Files should be cleaned up after context
    assert not os.path.exists(created_files[0])
    assert not os.path.exists(created_files[1])


def test_managed_temp_files_cleans_up_on_exception():
    """Test that files are cleaned up even when exceptions occur."""
    created_files = []
    
    try:
        with managed_temp_files('.mp3') as (file1,):
            created_files = [file1]
            assert os.path.exists(file1)
            raise ValueError("Test exception")
    except ValueError:
        pass  # Expected exception
    
    # File should still be cleaned up
    assert not os.path.exists(created_files[0])


@patch('subprocess.run')
def test_run_ffmpeg_safely_success(mock_run):
    """Test successful ffmpeg execution."""
    # Mock successful ffmpeg run
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""
    mock_run.return_value = mock_result
    
    cmd = ['ffmpeg', '-i', 'input.mp3', 'output.mp3']
    result = run_ffmpeg_safely(cmd)
    
    assert result.returncode == 0
    mock_run.assert_called_once_with(
        cmd, 
        capture_output=True, 
        text=True, 
        timeout=30,
        check=False
    )


@patch('subprocess.run')
def test_run_ffmpeg_safely_failure(mock_run):
    """Test ffmpeg execution with non-zero exit code."""
    # Mock failed ffmpeg run
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Error: Invalid input"
    mock_run.return_value = mock_result
    
    cmd = ['ffmpeg', '-i', 'input.mp3', 'output.mp3']
    result = run_ffmpeg_safely(cmd)
    
    assert result.returncode == 1
    assert "Invalid input" in result.stderr


@patch('builtins.open')
@patch('services.replicate_audio.run_ffmpeg_safely')
def test_sound_effect_processor_resource_management(mock_run, mock_open):
    """Test that SoundEffectProcessor properly manages resources."""
    from services.replicate_audio import SoundEffectProcessor
    
    # Mock ffmpeg to avoid actual execution
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result
    
    # Mock open for output file reading
    mock_open.return_value.__enter__.return_value.read.return_value = b'trimmed_audio_data'
    
    processor = SoundEffectProcessor()
    audio_data = b'original_audio_data'
    
    result = processor.trim_audio(audio_data)
    
    # Should return the mocked trimmed audio
    assert result == b'trimmed_audio_data'
    
    # Should have called ffmpeg safely
    mock_run.assert_called_once()
    ffmpeg_cmd = mock_run.call_args[0][0]
    assert ffmpeg_cmd[0] == 'ffmpeg'
    assert '-i' in ffmpeg_cmd 