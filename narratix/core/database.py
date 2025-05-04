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

def get_segments_for_text(text_id):
    session = Session()
    segments = session.query(Segment).filter(Segment.text_id == text_id).all()
    session.close()
    return segments
