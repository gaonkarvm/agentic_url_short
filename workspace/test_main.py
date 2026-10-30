import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from main import app, Base, get_db, URL

# Setup the test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_shortener.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the database tables
Base.metadata.create_all(bind=engine)

# Dependency override
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Setup: Clear the database before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # Teardown: Clear the database after each test
    Base.metadata.drop_all(bind=engine)

def test_create_short_url():
    response = client.post("/shorten", json={"original_url": "http://example.com"})
    assert response.status_code == 200
    data = response.json()
    assert "original_url" in data
    assert "short_url" in data
    assert "click_count" in data
    assert data["original_url"] == "http://example.com"
    assert data["click_count"] == 0

def test_redirect_to_original():
    # First, create a short URL
    response = client.post("/shorten", json={"original_url": "http://example.com"})
    assert response.status_code == 200
    short_url = response.json()["short_url"]

    # Then, test redirection
    response = client.get(f"/{short_url}")
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "http://example.com"
    assert data["short_url"] == short_url
    assert data["click_count"] == 1

def test_get_url_analytics():
    # First, create a short URL
    response = client.post("/shorten", json={"original_url": "http://example.com"})
    assert response.status_code == 200
    short_url = response.json()["short_url"]

    # Access the short URL to increase click count
    client.get(f"/{short_url}")

    # Then, test analytics
    response = client.get(f"/analytics/{short_url}")
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "http://example.com"
    assert data["short_url"] == short_url
    assert data["click_count"] == 1

def test_redirect_to_nonexistent_url():
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "URL not found"}

def test_get_analytics_for_nonexistent_url():
    response = client.get("/analytics/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "URL not found"}