# app/models/users.py

import enum
from sqlalchemy import Column, Integer, String, Enum
from app.database import Base

class UserRole(str, enum.Enum):
    """Enumeration for user roles."""
    USER = "user"
    ADMIN = "admin"

class User(Base):
    """SQLAlchemy model for the 'users' table."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)