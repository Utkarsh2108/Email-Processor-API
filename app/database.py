# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# The DATABASE_URL will be read from your .env file
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Remove the SQLite-specific connect_args from this call
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency to get a DB session for a request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()