import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import JWT_MINUTES, JWT_SECRET
from .db import get_db
from .models import ApiKey, User

password_hasher = PasswordHash.recommended()
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_password(raw: str) -> str:
    return password_hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return password_hasher.verify(raw, hashed)


def create_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=JWT_MINUTES)
    return jwt.encode({"sub": str(user.id), "exp": expires}, JWT_SECRET, algorithm="HS256")


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(User, int(data["sub"]))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def require_role(*allowed: str):
    def checker(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't do this")
        return user

    return checker


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_api_key() -> str:
    return "sop_" + secrets.token_urlsafe(32)


def require_api_key(
    raw: str | None = Security(api_key_header), db: Session = Depends(get_db)
) -> ApiKey:
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key")
    key = db.scalar(
        select(ApiKey).where(ApiKey.key_hash == hash_key(raw), ApiKey.active.is_(True))
    )
    if not key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    return key
