# app/schemas/user_schemas.py

from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr

class UserLogin(BaseModel):
    """Schema for user login request body."""
    email: EmailStr
    password: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    """User response model without roles."""
    id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Token data model without roles."""
    email: EmailStr
    user_id: int