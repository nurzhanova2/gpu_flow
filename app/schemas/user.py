import re
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.models.user import UserRole


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    full_name: str
    email: str
    team: str
    role: UserRole
    is_blocked: bool


class LoginRequest(BaseModel):
    username: Annotated[str, StringConstraints(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class RegisterRequest(BaseModel):
    username: Annotated[str, StringConstraints(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")]
    full_name: Annotated[str, StringConstraints(min_length=2, max_length=120)]
    email: Annotated[str, StringConstraints(min_length=6, max_length=254)]
    team: Annotated[str, StringConstraints(min_length=2, max_length=80)] = "general"
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]

    @field_validator("email")
    @classmethod
    def validate_registration_email(cls, value: str) -> str:
        email = value.strip().lower()
        if email.endswith(".local"):
            if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
                raise ValueError("invalid email")
            return email

        try:
            normalized = validate_email(email, check_deliverability=False).normalized
            return normalized
        except EmailNotValidError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("password must contain letters")
        if not re.search(r"\d", value):
            raise ValueError("password must contain digits")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
