from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import string
import random
from datetime import datetime

# Database setup
DATABASE_URL = "sqlite:///./shortener.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class URL(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_url = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    click_count = Column(Integer, default=0)

Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI()

# Pydantic models
class URLCreate(BaseModel):
    original_url: HttpUrl

class URLInfo(BaseModel):
    original_url: HttpUrl
    short_url: str
    click_count: int

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility functions
def generate_short_url():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

# Routes
@app.post("/shorten", response_model=URLInfo)
def create_short_url(url_create: URLCreate, db: Session = Depends(get_db)):
    short_url = generate_short_url()
    while db.query(URL).filter(URL.short_url == short_url).first():
        short_url = generate_short_url()

    db_url = URL(original_url=url_create.original_url, short_url=short_url)
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    return URLInfo(original_url=db_url.original_url, short_url=db_url.short_url, click_count=db_url.click_count)

@app.get("/{short_url}", response_model=URLInfo)
def redirect_to_original(short_url: str, db: Session = Depends(get_db)):
    db_url = db.query(URL).filter(URL.short_url == short_url).first()
    if db_url is None:
        raise HTTPException(status_code=404, detail="URL not found")

    db_url.click_count += 1
    db.commit()
    return URLInfo(original_url=db_url.original_url, short_url=db_url.short_url, click_count=db_url.click_count)

@app.get("/analytics/{short_url}", response_model=URLInfo)
def get_url_analytics(short_url: str, db: Session = Depends(get_db)):
    db_url = db.query(URL).filter(URL.short_url == short_url).first()
    if db_url is None:
        raise HTTPException(status_code=404, detail="URL not found")

    return URLInfo(original_url=db_url.original_url, short_url=db_url.short_url, click_count=db_url.click_count)