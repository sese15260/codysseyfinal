"""Request and response schemas for email signup."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    """Normalize and validate an email without requiring an extra package."""
    normalized_value = value.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized_value):
        raise ValueError("email must be a valid email address.")
    return normalized_value


class SignupRequest(BaseModel):
    name: str = Field(min_length=1)
    age: int = Field(gt=0)
    email: str
    password: str = Field(min_length=8)
    terms_agreed: Literal[True]
    privacy_agreed: Literal[True]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("name must not be blank.")
        return normalized_value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class SignupResponse(BaseModel):
    learner_id: str
    auth_user_id: str
    name: str
    age: int
    email: str


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    learner_id: str
    auth_user_id: str
    name: str
    age: int
    email: str


class CurrentLearnerResponse(BaseModel):
    learner_id: str
    auth_user_id: str
    name: str
    age: int
    email: str
