"""Auth-related schemas."""

from pydantic import BaseModel, Field


class RequestCodeIn(BaseModel):
    telegram_id: int


class CodeOut(BaseModel):
    code: str
    expires_in_minutes: int


class LoginIn(BaseModel):
    code: str = Field(..., min_length=4, max_length=12)


class AdminLoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class AccessOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
