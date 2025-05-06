from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from db.database import get_db
from db import crud, models

router = APIRouter(
    prefix="/api/character",
    tags=["character"],
)

class CharacterResponse(BaseModel):
    id: int
    text_id: int
    name: str
    description: Optional[str]
    provider_id: Optional[str]

@router.get("/text/{text_id}", response_model=List[CharacterResponse])
async def get_characters_by_text(
    text_id: int,
    db: Session = Depends(get_db)
):
    """Get all characters for a text"""
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(status_code=404, detail="Text not found")
    
    characters = crud.get_characters_by_text(db, text_id)
    
    return [{
        "id": char.id,
        "text_id": char.text_id,
        "name": char.name,
        "description": char.description,
        "provider_id": char.provider_id
    } for char in characters]

@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: int,
    character_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update a character"""
    db_character = db.query(models.Character).filter(models.Character.id == character_id).first()
    if not db_character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Update character fields
    if "name" in character_data:
        db_character.name = character_data["name"]
    if "description" in character_data:
        db_character.description = character_data["description"]
    if "provider_id" in character_data:
        db_character.provider_id = character_data["provider_id"]
    
    db.commit()
    db.refresh(db_character)
    
    return {
        "id": db_character.id,
        "text_id": db_character.text_id,
        "name": db_character.name,
        "description": db_character.description,
        "provider_id": db_character.provider_id
    }