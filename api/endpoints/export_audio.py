from fastapi import APIRouter, Depends, HTTPException, Response, BackgroundTasks, Path, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import os
import tempfile

from db.database import get_db
from db import crud
from services import combine_export_audio
from utils.config import settings
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/export",
    tags=["export"],
)

@router.post("/{text_id}/combine-speech", response_model=Dict[str, Any])
async def combine_speech_segments_endpoint(
    text_id: int = Path(..., description="ID of the text to process"),
    db: Session = Depends(get_db)
):
    """
    Combine all speech segments for a text into a single audio file.
    This also runs force alignment automatically.
    
    Args:
        text_id: ID of the text to process
        
    Returns:
        Processing status and combined audio file path
        
    Raises:
        404: Text not found
        400: No segments with audio found
        500: Combining failed
    """
    logger.info(f"Starting combine speech segments for text ID {text_id}")
    
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404, 
            detail=f"Text with ID {text_id} not found"
        )
    
    # Check if segments have audio data
    segments = crud.get_segments_by_text(db, text_id)
    segments_with_audio = [segment for segment in segments if segment.audio_data_b64]
    
    if not segments_with_audio:
        raise HTTPException(
            status_code=400,
            detail="No segments have audio generated. Generate speech first."
        )
    
    try:
        # Combine speech segments (includes force alignment)
        combined_audio_path = combine_export_audio.combine_speech_segments(db, text_id)
        
        if not combined_audio_path:
            raise HTTPException(
                status_code=500,
                detail="Failed to combine speech segments"
            )
        
        logger.info(f"Successfully combined speech segments for text ID {text_id}")
        
        return {
            "text_id": text_id,
            "status": "success",
            "message": "Speech segments combined successfully",
            "data": {
                "combined_audio_path": combined_audio_path,
                "segments_combined": len(segments_with_audio)
            }
        }
        
    except Exception as e:
        logger.error(f"Error combining speech segments for text ID {text_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Combining speech segments failed: {str(e)}"
        )

@router.post("/{text_id}/force-align", response_model=Dict[str, Any])
async def run_force_alignment(
    text_id: int = Path(..., description="ID of the text to process"),
    db: Session = Depends(get_db)
):
    """
    Run force alignment on combined speech to generate word-level timestamps.
    This combines speech segments first if not already done.
    
    Args:
        text_id: ID of the text to process
        
    Returns:
        Force alignment results with word timestamps
        
    Raises:
        404: Text not found
        400: No segments with audio found
        500: Force alignment failed
    """
    logger.info(f"Starting force alignment for text ID {text_id}")
    
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404,
            detail=f"Text with ID {text_id} not found"
        )

    # Check if segments have audio data
    segments = crud.get_segments_by_text(db, text_id)
    if not any(s.audio_data_b64 for s in segments):
        raise HTTPException(
            status_code=400,
            detail="Speech has not been generated for this text's segments. Please generate audio first."
        )

    try:
        # Force alignment is automatically handled in combine_speech_segments
        combined_audio_path = combine_export_audio.combine_speech_segments(db, text_id)
        success = combined_audio_path is not None

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Force alignment failed"
            )

        # Fetch the updated timestamps to return them
        updated_text = crud.get_text(db, text_id)
        
        logger.info(f"Successfully completed force alignment for text ID {text_id}")
        
        return {
            "text_id": text_id,
            "status": "success", 
            "message": "Force alignment completed successfully",
            "data": {
                "word_timestamps": updated_text.word_timestamps,
                "combined_audio_path": combined_audio_path
            }
        }
        
    except Exception as e:
        logger.error(f"Error in force alignment for text ID {text_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Force alignment failed: {str(e)}"
        )

@router.post("/{text_id}/final-audio", response_model=Dict[str, Any])
async def export_final_audio_endpoint(
    text_id: int = Path(..., description="ID of the text to process"),
    bg_volume: float = Query(0.15, description="Background music volume (0.0-1.0)"),
    fx_volume: float = Query(0.3, description="Sound effects volume (0.0-1.0)"),
    target_lufs: float = Query(-18.0, description="Target loudness in LUFS"),
    trailing_silence: float = Query(0.0, description="Trailing silence after each segment (seconds)"),
    db: Session = Depends(get_db)
):
    """
    Export final mixed audio with speech, background music, and sound effects.
    
    Args:
        text_id: ID of the text to process
        bg_volume: Background music volume (default 0.15 = 15%)
        fx_volume: Sound effects volume (default 0.3 = 30%)
        target_lufs: Target loudness in LUFS (default -18.0)
        trailing_silence: Trailing silence after segments (default 0.0)
        
    Returns:
        Export status and final audio file path
        
    Raises:
        404: Text not found
        400: No segments with audio found
        500: Export failed
    """
    logger.info(f"Starting final audio export for text ID {text_id}")
    
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404,
            detail=f"Text with ID {text_id} not found"
        )
    
    # Get segments to verify audio is generated
    segments = crud.get_segments_by_text(db, text_id)
    segments_with_audio = [segment for segment in segments if segment.audio_data_b64]
    
    if not segments_with_audio:
        raise HTTPException(
            status_code=400,
            detail="No segments have audio generated. Generate speech first."
        )
    
    try:
        # Export final audio with all processing
        audio_file = combine_export_audio.export_final_audio(
            db=db,
            text_id=text_id,
            bg_volume=bg_volume,
            trailing_silence=trailing_silence,
            target_lufs=target_lufs,
            fx_volume=fx_volume
        )
        
        if not audio_file:
            raise HTTPException(
                status_code=500,
                detail="Failed to export final audio"
            )
        
        logger.info(f"Successfully exported final audio for text ID {text_id}")
        
        return {
            "text_id": text_id,
            "status": "success",
            "message": "Final audio export completed successfully",
            "data": {
                "audio_file": audio_file,
                "parameters": {
                    "bg_volume": bg_volume,
                    "fx_volume": fx_volume,
                    "target_lufs": target_lufs,
                    "trailing_silence": trailing_silence
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error exporting final audio for text ID {text_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Final audio export failed: {str(e)}"
        )

@router.get("/{text_id}/status", response_model=Dict[str, Any])
async def get_export_status(
    text_id: int = Path(..., description="ID of the text to check status for"),
    db: Session = Depends(get_db)
):
    """
    Get export status for a text including available files and processing state.
    
    Args:
        text_id: ID of the text to check
        
    Returns:
        Export status with available files and processing state
        
    Raises:
        404: Text not found
    """
    logger.info(f"Getting export status for text ID {text_id}")
    
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404,
            detail=f"Text with ID {text_id} not found"
        )
    
    # Get segments with audio
    segments = crud.get_segments_by_text(db, text_id)
    segments_with_audio = [segment for segment in segments if segment.audio_data_b64]
    
    # Check for word timestamps (indicates force alignment completed)
    has_word_timestamps = bool(db_text.word_timestamps)
    
    # Check for background music
    has_background_music = bool(db_text.background_music_audio_b64)
    
    # Check for sound effects with audio
    sound_effects = crud.get_sound_effects_by_text(db, text_id)
    sound_effects_with_audio = [fx for fx in sound_effects if fx.audio_data_b64]
    
    # Check for exported files in output directory
    output_dir = os.path.join(os.getcwd(), "output")
    available_files = []
    
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if f"_{text_id}_" in filename:
                file_path = os.path.join(output_dir, filename)
                if os.path.isfile(file_path):
                    available_files.append({
                        "filename": filename,
                        "size": os.path.getsize(file_path),
                        "type": "combined_speech" if "combined_speech" in filename else 
                               "final_audio" if "final_audio" in filename else "unknown"
                    })
    
    # Determine overall status
    if not segments_with_audio:
        status = "no_audio"
    elif not has_word_timestamps:
        status = "speech_ready"
    elif available_files:
        status = "exported"
    else:
        status = "ready_to_export"
    
    return {
        "text_id": text_id,
        "status": status,
        "message": f"Export status for text {text_id}",
        "data": {
            "segments_count": len(segments),
            "segments_with_audio": len(segments_with_audio),
            "has_word_timestamps": has_word_timestamps,
            "has_background_music": has_background_music,
            "sound_effects_count": len(sound_effects),
            "sound_effects_with_audio": len(sound_effects_with_audio),
            "available_files": available_files
        }
    }

@router.get("/{text_id}/download/{filename}")
async def download_exported_file(
    text_id: int = Path(..., description="ID of the text"),
    filename: str = Path(..., description="Name of the file to download")
):
    """
    Download an exported file for a specific text.
    
    Args:
        text_id: ID of the text
        filename: Name of the file to download
        
    Returns:
        File content as response
        
    Raises:
        404: File not found or doesn't belong to text
        400: Invalid filename
    """
    logger.info(f"Download request for file '{filename}' for text ID {text_id}")
    
    # Validate filename contains text_id for security
    if f"_{text_id}_" not in filename:
        raise HTTPException(
            status_code=400,
            detail=f"File '{filename}' does not belong to text {text_id}"
        )
    
    # Check in output directory
    output_dir = os.path.join(os.getcwd(), "output")
    file_path = os.path.join(output_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"File '{filename}' not found"
        )
    
    try:
        # Read and return the file
        with open(file_path, "rb") as f:
            content = f.read()
        
        # Determine media type based on file extension
        if filename.endswith('.mp3'):
            media_type = "audio/mpeg"
        elif filename.endswith('.wav'):
            media_type = "audio/wav"
        else:
            media_type = "application/octet-stream"
        
        logger.info(f"Successfully served file '{filename}' for text ID {text_id}")
        
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error serving file '{filename}' for text ID {text_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {str(e)}"
        ) 