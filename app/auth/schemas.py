"""Pydantic request/response shapes for the auth router."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # ponytail: bare str, not EmailStr — mock creds are "admin@contadores"
    # which fails RFC validation. Add EmailStr when a real user store exists.
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UserPublic(BaseModel):
    id: str
    email: str
    name: str
    role: str


class TokenResponse(BaseModel):
    token: str
    user: UserPublic


class ErrorResponse(BaseModel):
    detail: str