from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import warnings

from db.database import get_db
from db import crud, models
from services import text_analysis

router = APIRouter(
    prefix="/api/text",
    tags=["text"],
)

class TextCreate(BaseModel):
    content: str
    title: Optional[str] = None

class TextResponse(BaseModel):
    id: int
    content: str
    title: Optional[str]
    analyzed: bool
    created: Optional[bool] = None

@router.post("/", response_model=TextResponse)
async def create_text(
    text_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Create a new text entry"""
    content = text_data.get("content")
    title = text_data.get("title")
    
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")
    
    # Check if text already exists
    existing_text = crud.get_text_by_content(db, content)
    if existing_text:
        return {
            "id": existing_text.id,
            "content": existing_text.content,
            "title": existing_text.title,
            "analyzed": existing_text.analyzed,
            "created": False
        }
    
    # Create new text
    db_text = crud.create_text(db, content, title)
    
    return {
        "id": db_text.id,
        "content": db_text.content,
        "title": db_text.title,
        "analyzed": db_text.analyzed,
        "created": True
    }

@router.get("/{text_id}", response_model=TextResponse)
async def get_text(
    text_id: int,
    db: Session = Depends(get_db)
):
    """Get a text by ID"""
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
    
    return {
        "id": db_text.id,
        "content": db_text.content,
        "title": db_text.title,
        "analyzed": db_text.analyzed
    }

@router.get("/", response_model=List[TextResponse])
async def list_texts(
    db: Session = Depends(get_db)
):
    """List all texts"""
    texts = db.query(models.Text).all()
    
    return [{
        "id": text.id,
        "content": text.content,
        "title": text.title,
        "analyzed": text.analyzed
    } for text in texts]

@router.put("/{text_id}/analyze", response_model=TextResponse)
async def analyze_text_endpoint(
    text_id: int,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    ⚠️ DEPRECATED: Use /api/text-analysis/{text_id}/analyze instead
    
    Analyze a text to extract characters and segments
    """
    warnings.warn(
        "This endpoint is deprecated. Use /api/text-analysis/{text_id}/analyze instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
    
    # Check if already analyzed and not forcing reanalysis
    if db_text.analyzed and not force:
        return {
            "id": db_text.id,
            "content": db_text.content,
            "title": db_text.title,
            "analyzed": db_text.analyzed
        }
    
    # Analyze text
    await text_analysis.process_text_analysis(db, text_id, db_text.content)
    
    # Return updated text
    db_text = crud.get_text(db, text_id)
    
    return {
        "id": db_text.id,
        "content": db_text.content,
        "title": db_text.title,
        "analyzed": db_text.analyzed
    }