import hmac
import hashlib
import jwt
import secrets
import time
from datetime import datetime, timedelta, timezone
from passlib.hash import bcrypt
from flask import Response, request
from werkzeug.exceptions import Unauthorized, Forbidden

from app.core.db import get_db
from app.core.settings import settings
from app.models.users import User

JWT_ALG = "HS256"
CSRF_TTL_SECONDS = 12 * 60 * 60  # 12 horas


def _secure_cookie_flag() -> bool:
    return settings.ENV != "dev"


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
        secure=_secure_cookie_flag(),
        path="/",
        max_age=max_age,
    )


def clear_session_cookie(res: Response):
    res.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        samesite="none",
        secure=_secure_cookie_flag(),
        path="/",
    )


def _sign_csrf_payload(payload: str) -> str:
    secret = settings.JWT_SECRET.encode("utf-8")
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_csrf_token(user_id: str) -> str:
    issued_at = int(time.time())
    nonce = secrets.token_urlsafe(16)
    payload = f"{user_id}:{issued_at}:{nonce}"
    signature = _sign_csrf_payload(payload)
    return f"{issued_at}:{nonce}:{signature}"


def set_csrf_cookie(res: Response, token: str, remember: bool):
    max_age = 1 * 24 * 60 * 60 if remember else None
    res.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        samesite="none",
        secure=_secure_cookie_flag(),
        path="/",
        max_age=max_age,
    )


def clear_csrf_cookie(res: Response):
    res.delete_cookie(
        key=settings.CSRF_COOKIE_NAME,
        httponly=False,
        samesite="none",
        secure=_secure_cookie_flag(),
        path="/",
    )


def _is_valid_csrf_token(user_id: str, token: str) -> bool:
    try:
        issued_raw, nonce, signature = token.split(":", 2)
        issued_at = int(issued_raw)
    except (ValueError, AttributeError):
        return False

    if (time.time() - issued_at) > CSRF_TTL_SECONDS:
        return False

    payload = f"{user_id}:{issued_at}:{nonce}"
    expected_signature = _sign_csrf_payload(payload)
    return hmac.compare_digest(signature, expected_signature)


def enforce_csrf(request_obj=None):
    req = request_obj or request
    header_token = req.headers.get("X-CSRF-Token")
    cookie_token = req.cookies.get(settings.CSRF_COOKIE_NAME)

    if not header_token or not cookie_token:
        raise Forbidden(description="CSRF token ausente")

    if not hmac.compare_digest(header_token, cookie_token):
        raise Forbidden(description="CSRF token inválido")

    user_id = get_current_user_id(req)
    if not _is_valid_csrf_token(user_id, header_token):
        raise Forbidden(description="CSRF token expirado ou inválido")


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
