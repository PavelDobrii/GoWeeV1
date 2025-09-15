import hashlib
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Generator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import User


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str = "secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    kafka_brokers: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


security = HTTPBearer()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def create_tokens(user: User) -> tuple[str, str]:
    now = datetime.utcnow()
    access_payload = {
        "sub": user.id,
        "type": "access",
        "token_version": user.token_version,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    refresh_payload = {
        "sub": user.id,
        "type": "refresh",
        "token_version": user.token_version,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    access = jwt.encode(
        access_payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    refresh = jwt.encode(
        refresh_payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return access, refresh


def decode_token(token: str, token_type: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
    if payload.get("type") != token_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials, "access")
    user = db.get(User, payload["sub"])
    if user is None or user.token_version != payload.get("token_version"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return user
