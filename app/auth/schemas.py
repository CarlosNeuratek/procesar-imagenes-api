"""Pydantic request/response shapes for the auth router."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


def _validate_email(value: str) -> str:
    # ponytail: custom validator instead of EmailStr so `admin@contadores` passes
    # (no TLD). One '@', at least one '.' after it. Strict RFC deferred.
    if "@" not in value:
        raise ValueError("email must contain '@'")
    local, _, domain = value.partition("@")
    if not local or not domain:
        raise ValueError("email must have local and domain parts")
    if "." not in domain:
        raise ValueError("email domain must contain '.'")
    return value


class Role(str, Enum):
    admin = "admin"
    contador = "contador"


class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _validate_email(v)


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


class UserCreate(BaseModel):
    email: str
    name: str
    role: Role
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _validate_email(v)