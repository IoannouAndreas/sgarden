"""Pydantic models for users and authentication."""
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload for registering a new user."""
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    """Payload for logging in."""
    username: str
    password: str


class AuthResponse(BaseModel):
    """Response returned after successful auth."""
    token: str
    username: str
    role: str
