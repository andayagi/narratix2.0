from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, Literal
from pydantic import BaseModel

from db.database import get_db
from db import crud
from utils.logging import get_logger

router = APIRouter(
    prefix="/replicate-webhook",
    tags=["Replicate Webhooks"],
    responses={404: {"description": "Not found"}},
)

logger = get_logger(__name__)

class WebhookPayload(BaseModel):
    """Replicate webhook payload structure"""
    id: str
    version: str
    created_at: str
    started_at: str = None
    completed_at: str = None
    status: Literal["starting", "processing", "succeeded", "failed", "canceled"]
    input: Dict[str, Any]
    output: Any = None
    error: str = None
    logs: str = None
    metrics: Dict[str, Any] = None

@router.post("/{content_type}/{content_id}")
async def handle_replicate_webhook(
    content_type: Literal["sound_effect", "background_music"],
    content_id: int,
    payload: WebhookPayload,
    background_tasks: BackgroundTasks, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Unified webhook handler for Replicate predictions.
    Routes to appropriate processing based on content_type.
    
    Args:
        content_type: "sound_effect" or "background_music"
        content_id: effect_id for sound_effect, text_id for background_music
        payload: Replicate webhook payload
        background_tasks: FastAPI background tasks
        request: HTTP request for logging
        db: Database session
    """
    
    # Log webhook receipt
    logger.info(
        f"Received webhook for {content_type} {content_id}",
        extra={
            "context": {
                "content_type": content_type,
                "content_id": content_id,
                "prediction_id": payload.id,
                "status": payload.status
            }
        }
    )
    
    try:
        # Validate content exists
        if content_type == "sound_effect":
            content = crud.get_sound_effect(db, content_id)
            if not content:
                raise HTTPException(status_code=404, detail=f"Sound effect {content_id} not found")
        elif content_type == "background_music":
            content = crud.get_text(db, content_id)
            if not content:
                raise HTTPException(status_code=404, detail=f"Text {content_id} not found")
        
        # Handle different prediction statuses
        if payload.status == "succeeded":
            if not payload.output:
                logger.error(
                    f"Webhook succeeded but no output provided for {content_type} {content_id}",
                    extra={"context": {"prediction_id": payload.id, "payload": payload.dict()}}
                )
                raise HTTPException(status_code=400, detail="Webhook succeeded but no output provided")
            
            # Process in background
            background_tasks.add_task(
                process_webhook_success,
                content_type,
                content_id,
                payload.dict(),
                db_session_factory=get_db
            )
            
            logger.info(
                f"Queued background processing for successful {content_type} {content_id}",
                extra={"context": {"prediction_id": payload.id}}
            )
            
        elif payload.status == "failed":
            # Log failure
            logger.error(
                f"Replicate prediction failed for {content_type} {content_id}",
                extra={
                    "context": {
                        "prediction_id": payload.id,
                        "error": payload.error,
                        "logs": payload.logs
                    }
                }
            )
            
            # Update database to mark as failed
            background_tasks.add_task(
                mark_generation_failed,
                content_type,
                content_id,
                payload.error or "Generation failed",
                db_session_factory=get_db
            )
            
        elif payload.status == "canceled":
            logger.warning(
                f"Replicate prediction canceled for {content_type} {content_id}",
                extra={"context": {"prediction_id": payload.id}}
            )
            
            # Update database to mark as canceled
            background_tasks.add_task(
                mark_generation_failed,
                content_type,
                content_id,
                "Generation canceled",
                db_session_factory=get_db
            )
            
        elif payload.status in ["starting", "processing"]:
            # Just log progress
            logger.info(
                f"Replicate prediction {payload.status} for {content_type} {content_id}",
                extra={"context": {"prediction_id": payload.id}}
            )
        
        return {"message": f"Webhook processed for {content_type} {content_id}", "status": payload.status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error processing webhook for {content_type} {content_id}",
            exc_info=True,
            extra={
                "context": {
                    "prediction_id": payload.id,
                    "error": str(e)
                }
            }
        )
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

async def process_webhook_success(
    content_type: str,
    content_id: int,
    payload_data: Dict[str, Any],
    db_session_factory
):
    """
    Process successful webhook in background.
    Routes to appropriate processing function based on content_type.
    """
    db = next(db_session_factory())
    
    try:
        if content_type == "sound_effect":
            await process_sound_effect_webhook_result(db, content_id, payload_data)
        elif content_type == "background_music":
            await process_background_music_webhook_result(db, content_id, payload_data)
            
        logger.info(
            f"Successfully processed webhook result for {content_type} {content_id}",
            extra={"context": {"prediction_id": payload_data.get("id")}}
        )
        
    except Exception as e:
        logger.error(
            f"Error in background processing for {content_type} {content_id}",
            exc_info=True,
            extra={
                "context": {
                    "prediction_id": payload_data.get("id"),
                    "error": str(e)
                }
            }
        )
    finally:
        db.close()

async def process_sound_effect_webhook_result(db: Session, effect_id: int, payload_data: Dict[str, Any]):
    """Process sound effect webhook result - TODO: implement with shared audio processing"""
    # This will be implemented in the next task when we create the shared audio processing
    logger.info(f"TODO: Process sound effect {effect_id} webhook result")
    pass

async def process_background_music_webhook_result(db: Session, text_id: int, payload_data: Dict[str, Any]):
    """Process background music webhook result - TODO: implement with shared audio processing"""
    # This will be implemented in the next task when we create the shared audio processing
    logger.info(f"TODO: Process background music {text_id} webhook result")
    pass

async def mark_generation_failed(
    content_type: str,
    content_id: int,
    error_message: str,
    db_session_factory
):
    """Mark generation as failed in database"""
    db = next(db_session_factory())
    
    try:
        # Log the failure - actual database updates will be implemented
        # when we have the shared audio processing infrastructure
        logger.error(
            f"Marking {content_type} {content_id} as failed: {error_message}",
            extra={
                "context": {
                    "content_type": content_type,
                    "content_id": content_id,
                    "error": error_message
                }
            }
        )
        
        # TODO: Update database records to mark as failed
        # This will be implemented with the shared audio processing
        
    except Exception as e:
        logger.error(
            f"Error marking {content_type} {content_id} as failed",
            exc_info=True,
            extra={"context": {"error": str(e)}}
        )
    finally:
        db.close() 