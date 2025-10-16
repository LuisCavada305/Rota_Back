import hmac
import hashlib
import jwt
import secrets
import time
from datetime import datetime, timedelta, timezone
from passlib.hash import bcrypt
from flask import Response, request, has_request_context
from werkzeug.exceptions import Unauthorized, Forbidden

from app.core.db import get_db
from app.core.settings import settings
from app.models.users import User

JWT_ALG = "HS256"
CSRF_TTL_SECONDS = 12 * 60 * 60  # 12 horas
PASSWORD_RESET_TTL = timedelta(hours=1)


def _secure_cookie_flag() -> bool:
    if settings.ENV != "dev":
        return True

    if not has_request_context():
        return False

    if request.is_secure:
        return True

    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    if forwarded_proto.lower().split(",", 1)[0].strip() == "https":
        return True

    return False


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


def generate_password_reset_token(
    user: User, expires_in: timedelta = PASSWORD_RESET_TTL
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.user_id),
        "email": user.email,
        "type": "password_reset",
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALG)


def decode_password_reset_token(token: str) -> dict[str, str | int]:
    try:
        decoded = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[JWT_ALG],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.PyJWTError:
        raise Unauthorized(description="Token de redefinição inválido ou expirado")

    if decoded.get("type") != "password_reset":
        raise Unauthorized(description="Token de redefinição inválido ou expirado")

    try:
        user_id = int(decoded["sub"])
    except (KeyError, TypeError, ValueError):
        raise Unauthorized(description="Token de redefinição inválido ou expirado")

    email = decoded.get("email")
    if not email:
        raise Unauthorized(description="Token de redefinição inválido ou expirado")

    return {"user_id": user_id, "email": email}


def set_session_cookie(res: Response, token: str, remember: bool):
    # remember -> 1 dia; caso contrário, cookie de sessão
    max_age = 1 * 24 * 60 * 60 if remember else None
    secure_flag = _secure_cookie_flag()
    samesite_mode = "none" if secure_flag else "lax"
    res.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite=samesite_mode,
        secure=secure_flag,
        path="/",
        max_age=max_age,
    )


def clear_session_cookie(res: Response):
    secure_flag = _secure_cookie_flag()
    samesite_mode = "none" if secure_flag else "lax"
    res.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        samesite=samesite_mode,
        secure=secure_flag,
        path="/",
    )


def _csrf_secret() -> bytes:
    secret = settings.CSRF_SECRET or settings.JWT_SECRET
    return secret.encode("utf-8")


def _sign_csrf_payload(payload: str) -> str:
    secret = _csrf_secret()
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_csrf_token(user_id: str) -> str:
    issued_at = int(time.time())
    nonce = secrets.token_urlsafe(16)
    payload = f"{user_id}:{issued_at}:{nonce}"
    signature = _sign_csrf_payload(payload)
    return f"{issued_at}:{nonce}:{signature}"


def set_csrf_cookie(res: Response, token: str, remember: bool):
    max_age = 1 * 24 * 60 * 60 if remember else None
    secure_flag = _secure_cookie_flag()
    samesite_mode = "none" if secure_flag else "lax"
    res.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        samesite=samesite_mode,
        secure=secure_flag,
        path="/",
        max_age=max_age,
    )


def clear_csrf_cookie(res: Response):
    secure_flag = _secure_cookie_flag()
    samesite_mode = "none" if secure_flag else "lax"
    res.delete_cookie(
        key=settings.CSRF_COOKIE_NAME,
        httponly=False,
        samesite=samesite_mode,
        secure=secure_flag,
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
    header_token = None
    # Accept common header spellings so different clients can reuse the same token value
    normalized_headers = {k.lower(): v for k, v in req.headers.items()}
    header_candidates = (
        "x-csrf-token",
        "x-csrftoken",
        "x-xsrf-token",
        "x-xsrftoken",
        settings.CSRF_COOKIE_NAME.lower(),
    )
    for header_name in header_candidates:
        header_token = normalized_headers.get(header_name)
        if header_token:
            break
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


def require_roles(*roles: str) -> User:
    user = get_current_user()
    if user.role_code not in roles:
        raise FORBID
    return user
