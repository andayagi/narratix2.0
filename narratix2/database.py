from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, exists
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import hashlib

Base = declarative_base()
engine = create_engine('sqlite:///narratix.db')
Session = sessionmaker(bind=engine)

class TextContent(Base):
    __tablename__ = 'texts'
    
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), unique=True, nullable=False)
    characters = relationship("Character", back_populates="text")
    segments = relationship("Segment", back_populates="text")

    @staticmethod
    def calculate_hash(content):
        return hashlib.sha256(content.encode()).hexdigest()

class Character(Base):
    __tablename__ = 'characters'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    text_id = Column(Integer, ForeignKey('texts.id'))
    text = relationship("TextContent", back_populates="characters")
    segments = relationship("Segment", back_populates="character")

class Segment(Base):
    __tablename__ = 'segments'
    
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)
    text_id = Column(Integer, ForeignKey('texts.id'))
    character_id = Column(Integer, ForeignKey('characters.id'))
    text = relationship("TextContent", back_populates="segments")
    character = relationship("Character", back_populates="segments")

def init_db():
    Base.metadata.create_all(engine)

# CRUD Operations
def create_text(content):
    session = Session()
    content_hash = TextContent.calculate_hash(content)
    text = TextContent(content=content, content_hash=content_hash)
    session.add(text)
    session.commit()
    text_id = text.id
    session.close()
    return text_id

def create_character(name, description, text_id):
    session = Session()
    character = Character(name=name, description=description, text_id=text_id)
    session.add(character)
    session.commit()
    character_id = character.id
    session.close()
    return character_id

def create_segment(content, start_index, end_index, text_id, character_id):
    session = Session()
    segment = Segment(
        content=content,
        start_index=start_index,
        end_index=end_index,
        text_id=text_id,
        character_id=character_id
    )
    session.add(segment)
    session.commit()
    segment_id = segment.id
    session.close()
    return segment_id

def text_exists(content):
    session = Session()
    content_hash = TextContent.calculate_hash(content)
    exists_query = session.query(exists().where(TextContent.content_hash == content_hash)).scalar()
    session.close()
    return exists_query

def get_characters_for_text(text_id):
    session = Session()
    characters = session.query(Character).filter(Character.text_id == text_id).all()
    session.close()
    return characters

def get_segments_for_text(text_id):
    session = Session()
    segments = session.query(Segment).filter(Segment.text_id == text_id).all()
    session.close()
    return segments

def get_text_by_id(text_id):
    session = Session()
    text = session.query(TextContent).get(text_id)
    session.close()
    return text

def update_text(text_id, content):
    session = Session()
    text = session.query(TextContent).get(text_id)
    if text:
        text.content = content
        text.content_hash = TextContent.calculate_hash(content)
        session.commit()
    session.close()
    return text is not None

def update_character(character_id, name=None, description=None):
    session = Session()
    character = session.query(Character).get(character_id)
    if character:
        if name:
            character.name = name
        if description:
            character.description = description
        session.commit()
    session.close()
    return character is not None

def delete_text(text_id):
    session = Session()
    text = session.query(TextContent).get(text_id)
    if text:
        session.delete(text)
        session.commit()
    session.close()
    return text is not None

def delete_character(character_id):
    session = Session()
    character = session.query(Character).get(character_id)
    if character:
        session.delete(character)
        session.commit()
    session.close()
    return character is not None

def delete_segment(segment_id):
    session = Session()
    segment = session.query(Segment).get(segment_id)
    if segment:
        session.delete(segment)
        session.commit()
    session.close()
    return segment is not None 