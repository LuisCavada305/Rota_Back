import jwt
from datetime import datetime, timedelta, timezone
from passlib.hash import bcrypt
from flask import Response, request
from werkzeug.exceptions import Unauthorized, Forbidden

from app.core.db import get_db
from app.core.settings import settings
from app.models.users import User

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
    # remember -> 1 dia; caso contrário, cookie de sessão
    max_age = 1 * 24 * 60 * 60 if remember else None
    res.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="none",  # se front/back estiverem em domínios diferentes
        secure=True,  # True em produção (HTTPS)
        path="/",
        max_age=max_age,
    )


def clear_session_cookie(res: Response):
    res.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        samesite="none",
        secure=(settings.ENV != "dev"),
        path="/",
    )


def get_current_user_id(req=None) -> str:
    req = req or request
    token = req.cookies.get(settings.COOKIE_NAME)
    if not token:
        raise Unauthorized(description="Não autenticado")
    try:
        decoded = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )
        return decoded["id"]
    except jwt.PyJWTError:
        raise Unauthorized(description="Sessão inválida")


def get_current_user() -> User:
    user_id = get_current_user_id()
    db = get_db()
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise Unauthorized(description="Não autenticado")
    return user


FORBID = Forbidden(description="Sem permissão")
