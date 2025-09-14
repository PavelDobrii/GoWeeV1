from typing import Optional

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(RegisterRequest):
    pass


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ProfileResponse(ProfileUpdate):
    email: EmailStr

    class Config:
        from_attributes = True


class ConsentsUpdate(BaseModel):
    marketing: bool
    terms: bool


class ConsentsResponse(ConsentsUpdate):
    class Config:
        from_attributes = True
