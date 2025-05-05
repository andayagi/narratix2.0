from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import uuid
from pydantic import BaseModel

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
    id: str
    content: str
    title: Optional[str]
    analyzed: bool

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
            "id": str(existing_text.id),
            "content": existing_text.content,
            "title": existing_text.title,
            "analyzed": existing_text.analyzed
        }
    
    # Create new text
    db_text = crud.create_text(db, content, title)
    
    return {
        "id": str(db_text.id),
        "content": db_text.content,
        "title": db_text.title,
        "analyzed": db_text.analyzed
    }

@router.get("/{text_id}", response_model=TextResponse)
async def get_text(
    text_id: str,
    db: Session = Depends(get_db)
):
    """Get a text by ID"""
    try:
        text_uuid = uuid.UUID(text_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
        
    db_text = crud.get_text(db, text_uuid)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
    
    return {
        "id": str(db_text.id),
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
        "id": str(text.id),
        "content": text.content,
        "title": text.title,
        "analyzed": text.analyzed
    } for text in texts]

@router.put("/{text_id}/analyze", response_model=TextResponse)
async def analyze_text_endpoint(
    text_id: str,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """Analyze a text to extract characters and segments"""
    try:
        text_uuid = uuid.UUID(text_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
        
    db_text = crud.get_text(db, text_uuid)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
    
    # Check if already analyzed and not forcing reanalysis
    if db_text.analyzed and not force:
        return {
            "id": str(db_text.id),
            "content": db_text.content,
            "title": db_text.title,
            "analyzed": db_text.analyzed
        }
    
    # Analyze text
    text_analysis.process_text_analysis(db, text_uuid, db_text.content)
    
    # Return updated text
    db_text = crud.get_text(db, text_uuid)
    
    return {
        "id": str(db_text.id),
        "content": db_text.content,
        "title": db_text.title,
        "analyzed": db_text.analyzed
    }