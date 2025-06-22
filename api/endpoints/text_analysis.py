from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Path, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from db.database import get_db
from db import crud, models
from services import text_analysis
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/text-analysis",
    tags=["text-analysis"],
    responses={404: {"description": "Text not found"}}
)

class TextAnalysisResponse(BaseModel):
    text_id: int
    status: str
    message: str
    data: Dict[str, Any] = {}

class CharacterResponse(BaseModel):
    id: int
    name: str
    is_narrator: bool
    persona_description: Optional[str] = None
    intro_text: Optional[str] = None
    provider: Optional[str] = None
    provider_id: Optional[str] = None

class SegmentResponse(BaseModel):
    id: int
    sequence: int
    character_name: str = None
    content: str
    speed: float = None
    trailing_silence: float = None

@router.post("/{text_id}/analyze", status_code=202)
async def analyze_text_full(
    text_id: int = Path(..., description="ID of the text to analyze"),
    skip_if_analyzed: bool = Query(False, description="Skip analysis if already analyzed"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Run full text analysis to extract characters and segments.
    
    By default, this will always reprocess the text, deleting existing characters/segments
    and making fresh calls to Anthropic API.
    
    Args:
        text_id: ID of the text to analyze
        skip_if_analyzed: Skip analysis if text is already marked as analyzed
        
    Returns:
        Processing status and details
        
    Raises:
        404: Text not found
        400: Text content is empty
        500: Analysis error
    """
    logger.info(f"Starting full text analysis for text ID {text_id}")
    
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404, 
            detail=f"Text with ID {text_id} not found"
        )
    
    # Check if content exists
    if not db_text.content or not db_text.content.strip():
        raise HTTPException(
            status_code=400,
            detail="Text content is empty"
        )
    
    # Check if should skip if already analyzed
    if db_text.analyzed and skip_if_analyzed:
        logger.info(f"Text {text_id} already analyzed, skipping reanalysis")
        return TextAnalysisResponse(
            text_id=text_id,
            status="completed", 
            message="Text already analyzed. Set skip_if_analyzed=false to reanalyze.",
            data={"analyzed": True}
        )
    
    try:
        # Run analysis in background if BackgroundTasks is available
        if background_tasks:
            background_tasks.add_task(
                text_analysis.process_text_analysis, 
                db, text_id, db_text.content
            )
            return TextAnalysisResponse(
                text_id=text_id,
                status="processing",
                message="Text analysis initiated in background"
            )
        else:
            # Run synchronously
            await text_analysis.process_text_analysis(db, text_id, db_text.content)
            logger.info(f"Successfully completed text analysis for text ID {text_id}")
            return TextAnalysisResponse(
                text_id=text_id,
                status="completed",
                message="Text analysis completed successfully"
            )
            
    except Exception as e:
        logger.error(f"Error in text analysis for text ID {text_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Text analysis failed: {str(e)}"
        )

@router.post("/{text_id}/characters", status_code=202)
async def extract_characters(
    text_id: int = Path(..., description="ID of the text to extract characters from"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Extract characters only from text (Phase 1 of analysis).
    
    Args:
        text_id: ID of the text to process
        
    Returns:
        Processing status and details
        
    Raises:
        404: Text not found
        400: Text content is empty
        500: Character extraction error
    """
    logger.info(f"Starting character extraction for text ID {text_id}")
    
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404, 
            detail=f"Text with ID {text_id} not found"
        )
    
    if not db_text.content or not db_text.content.strip():
        raise HTTPException(
            status_code=400,
            detail="Text content is empty"
        )
    
    try:
        # Extract characters using phase 1 analysis
        characters = text_analysis.analyze_text_phase1_characters(db_text.content)
        
        # Store characters in database (simplified version of full analysis)
        for char_data in characters:
            existing_char = crud.get_character_by_name_and_text(db, char_data["name"], text_id)
            if not existing_char:
                crud.create_character(
                    db=db,
                    text_id=text_id,
                    name=char_data["name"],
                    is_narrator=char_data["is_narrator"],
                    persona_description=char_data["persona_description"],
                    intro_text=char_data.get("text", "")
                )
        
        logger.info(f"Successfully extracted {len(characters)} characters for text ID {text_id}")
        return TextAnalysisResponse(
            text_id=text_id,
            status="completed",
            message=f"Successfully extracted {len(characters)} characters",
            data={"characters_count": len(characters)}
        )
        
    except Exception as e:
        logger.error(f"Error extracting characters for text ID {text_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Character extraction failed: {str(e)}"
        )

@router.post("/{text_id}/segments", status_code=202)
async def extract_segments(
    text_id: int = Path(..., description="ID of the text to extract segments from"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Extract segments only from text (Phase 2 of analysis).
    
    Args:
        text_id: ID of the text to extract segments from
        
    Returns:
        Processing status and details
        
    Raises:
        404: Text not found
        400: Prerequisites not met
        500: Segment extraction error
    """
    logger.info(f"Starting segment extraction for text ID {text_id}")
    
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404, 
            detail=f"Text with ID {text_id} not found"
        )
    
    if not db_text.content or not db_text.content.strip():
        raise HTTPException(
            status_code=400,
            detail="Text content is empty"
        )
    
    # Check if characters exist (prerequisite for segmentation)
    characters = crud.get_characters_by_text(db, text_id)
    if not characters:
        raise HTTPException(
            status_code=400,
            detail="Characters must be extracted before segment extraction. Run /characters endpoint first."
        )
    
    try:
        # Convert characters to the format expected by phase 2
        character_details = []
        for char in characters:
            character_details.append({
                "name": char.name,
                "is_narrator": char.is_narrator,
                "speaking": True,
                "persona_description": char.persona_description,
                "text": char.intro_text or ""
            })
        
        # Extract segments using phase 2 analysis
        segments = text_analysis.analyze_text_phase2_segmentation(db_text.content, character_details)
        
        # Store segments in database (simplified version)
        for i, segment_data in enumerate(segments):
            crud.create_text_segment(
                db=db,
                text_id=text_id,
                sequence_order=i + 1,
                character_name=segment_data["role"],
                content=segment_data["text"],
                element_type=segment_data.get("description", "dialogue"),
                speed=segment_data.get("speed"),
                trailing_silence=segment_data.get("trailing_silence")
            )
        
        logger.info(f"Successfully extracted {len(segments)} segments for text ID {text_id}")
        return TextAnalysisResponse(
            text_id=text_id,
            status="completed",
            message=f"Successfully extracted {len(segments)} segments",
            data={"segments_count": len(segments)}
        )
        
    except Exception as e:
        logger.error(f"Error extracting segments for text ID {text_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Segment extraction failed: {str(e)}"
        )

@router.get("/{text_id}")
async def get_text_analysis_results(
    text_id: int = Path(..., description="ID of the text to get analysis results for"),
    db: Session = Depends(get_db)
):
    """
    Get complete text analysis results including characters and segments.
    
    Args:
        text_id: ID of the text
        
    Returns:
        Complete analysis results
        
    Raises:
        404: Text not found
        400: Text not analyzed
    """
    logger.info(f"Retrieving text analysis results for text ID {text_id}")
    
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404, 
            detail=f"Text with ID {text_id} not found"
        )
    
    # Check if analyzed
    if not db_text.analyzed:
        raise HTTPException(
            status_code=400,
            detail="Text has not been analyzed yet. Run /analyze endpoint first."
        )
    
    # Get characters and segments
    characters = crud.get_characters_by_text(db, text_id)
    segments = crud.get_segments_by_text(db, text_id)
    
    # Log character details for debugging
    logger.info(f"Retrieved {len(characters)} characters for text {text_id}")
    for char in characters:
        logger.info(f"Character {char.id}: name='{char.name}', provider='{char.provider}', provider_id='{char.provider_id}'")
    
    return TextAnalysisResponse(
        text_id=text_id,
        status="completed",
        message="Analysis results retrieved successfully",
        data={
            "analyzed": db_text.analyzed,
            "characters_count": len(characters),
            "segments_count": len(segments),
            "characters": [
                CharacterResponse(
                    id=char.id,
                    name=char.name,
                    is_narrator=char.is_narrator,
                    persona_description=char.persona_description or "",
                    intro_text=char.intro_text or "",
                    provider=char.provider,
                    provider_id=char.provider_id
                ) for char in characters
            ],
            "segments": [
                SegmentResponse(
                    id=seg.id,
                    sequence=seg.sequence,
                    character_name=seg.character.name if seg.character else None,
                    content=seg.text,
                    speed=seg.speed,
                    trailing_silence=seg.trailing_silence
                ) for seg in segments
            ]
        }
    )

@router.get("/{text_id}/characters")
async def get_characters(
    text_id: int = Path(..., description="ID of the text to get characters for"),
    db: Session = Depends(get_db)
):
    """
    Get characters extracted from text analysis.
    
    Args:
        text_id: ID of the text
        
    Returns:
        List of characters
        
    Raises:
        404: Text not found
        400: No characters found
    """
    logger.info(f"Retrieving characters for text ID {text_id}")
    
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404, 
            detail=f"Text with ID {text_id} not found"
        )
    
    # Get characters
    characters = crud.get_characters_by_text(db, text_id)
    if not characters:
        raise HTTPException(
            status_code=400,
            detail="No characters found. Run character extraction first."
        )
    
    return TextAnalysisResponse(
        text_id=text_id,
        status="completed",
        message=f"Retrieved {len(characters)} characters",
        data={
            "characters": [
                CharacterResponse(
                    id=char.id,
                    name=char.name,
                    is_narrator=char.is_narrator,
                    persona_description=char.persona_description or "",
                    intro_text=char.intro_text or "",
                    provider=char.provider,
                    provider_id=char.provider_id
                ) for char in characters
            ]
        }
    )

@router.get("/{text_id}/segments")
async def get_segments(
    text_id: int = Path(..., description="ID of the text to get segments for"),
    db: Session = Depends(get_db)
):
    """
    Get segments extracted from text analysis.
    
    Args:
        text_id: ID of the text
        
    Returns:
        List of segments
        
    Raises:
        404: Text not found
        400: No segments found
    """
    logger.info(f"Retrieving segments for text ID {text_id}")
    
    # Validate text exists
    db_text = crud.get_text(db, text_id)
    if not db_text:
        raise HTTPException(
            status_code=404, 
            detail=f"Text with ID {text_id} not found"
        )
    
    # Get segments
    segments = crud.get_segments_by_text(db, text_id)
    if not segments:
        raise HTTPException(
            status_code=400,
            detail="No segments found. Run segment extraction first."
        )
    
    return TextAnalysisResponse(
        text_id=text_id,
        status="completed",
        message=f"Retrieved {len(segments)} segments",
        data={
            "segments": [
                SegmentResponse(
                    id=seg.id,
                    sequence=seg.sequence,
                    character_name=seg.character.name if seg.character else None,
                    content=seg.text,
                    speed=seg.speed,
                    trailing_silence=seg.trailing_silence
                ) for seg in segments
            ]
        }
    ) 