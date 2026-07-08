from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.app.config import DATABASE_URL

# Create SQL Engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Safe for SQLite multithread usage
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base
Base = declarative_base()

def get_db():
    """Dependency helper to get database session and ensure clean close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
