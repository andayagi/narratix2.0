import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import uuid

from api.main import app
from db.database import Base, get_db

# Create test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Set up test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function")
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_create_text(setup_database):
    response = client.post(
        "/api/text/",
        json={
            "content": "This is a test story. Alice said, 'Hello!' Bob replied, 'Hi Alice!'",
            "title": "Test Story"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Story"
    assert data["analyzed"] == False
    
    # Test retrieving the text
    text_id = data["id"]
    response = client.get(f"/api/text/{text_id}")
    assert response.status_code == 200
    assert response.json()["content"] == "This is a test story. Alice said, 'Hello!' Bob replied, 'Hi Alice!'"

# More tests would be added for a complete implementation