import logging
from contextlib import asynccontextmanager
from typing import Literal

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import ADMIN_EMAIL, ADMIN_PASSWORD, DATABASE_URL
from .db import Base, SessionLocal, engine, get_db
from .middleware import RequestLogMiddleware
from .models import ApiKey, User
from .security import (
    create_token, current_user, hash_key, hash_password, new_api_key,
    require_api_key, require_role, verify_password,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == ADMIN_EMAIL)):
            db.add(User(email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD), role="admin"))
            db.commit()
    yield


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="SOP Automator API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(RequestLogMiddleware)


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=10)
    role: Literal["admin", "instructor", "student"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: str


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


@app.get("/api/health")
def health():
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        db = "ok"
    except Exception:
        db = "down"
    return {"api": "ok", "db": db}


@app.post("/api/auth/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    return {"access_token": create_token(user), "token_type": "bearer"}


@app.get("/api/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "instructor")),
):
    return db.scalars(select(User).order_by(User.id)).all()


@app.post("/api/users", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "That email already exists")
    user = User(email=email, password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/api-keys", status_code=201)
def create_api_key(
    body: ApiKeyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    raw = new_api_key()
    db.add(ApiKey(name=body.name, prefix=raw[:8], key_hash=hash_key(raw)))
    db.commit()
    return {"name": body.name, "api_key": raw, "note": "Copy this now. It won't be shown again."}


@app.get("/api/integrations/ping")
def integrations_ping(key: ApiKey = Depends(require_api_key)):
    return {"ok": True, "key_name": key.name}
