"""User authentication and profile data models."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserRegister(BaseModel):
    """Schema for user registration."""
    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=6, max_length=100, description="Password (min 6 characters)")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    gender: Optional[str] = Field(None, description="Gender (male/female/other)")


class UserLogin(BaseModel):
    """Schema for user login."""
    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class UserResponse(BaseModel):
    """Safe user response (excludes password)."""
    id: str = Field(..., description="User ID")
    name: str
    email: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
