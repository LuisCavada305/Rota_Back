import jwt
from datetime import datetime, timedelta, timezone
from passlib.hash import bcrypt
from fastapi import Response
from core.settings import settings
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from models.users import User
from core.db import get_db

JWT_ALG = "HS256"

def hash_password(password: str) -> str:
    return bcrypt.hash(password)

def verify_password(password: str, password_hash: str | bytes) -> bool:
    return bcrypt.verify(password, password_hash)

def sign_session(payload: dict, expires_in: timedelta = timedelta(days=1)) -> str:
    now = datetime.now(timezone.utc)
    to_encode = {
        "iat": now,
        "exp": now + expires_in,
        **payload,
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=JWT_ALG)

def set_session_cookie(res: Response, token: str, remember: bool):
    # remember -> 30 dias; caso contrário, cookie de sessão
    max_age = 30 * 24 * 60 * 60 if remember else None
    res.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="true",                     # se front/back estiverem em domínios diferentes
        secure=(settings.ENV != "dev"),      # True em produção (HTTPS)
        path="/",
        max_age=max_age
    )

def clear_session_cookie(res: Response):
    res.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        samesite="true",
        secure=(settings.ENV != "dev"),
        path="/",
    )


UNAUTH = HTTPException(status_code=401, detail="Não autenticado")
FORBID = HTTPException(status_code=403, detail="Sem permissão")

def get_current_user_id(request: Request) -> str:
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        raise UNAUTH
    try:
        decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return decoded["id"]
    except jwt.PyJWTError:
        raise UNAUTH

def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UNAUTH
    return user
