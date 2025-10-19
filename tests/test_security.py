import uuid

import pytest
from werkzeug.exceptions import Forbidden, Unauthorized

from app.core.settings import settings
from app.main import app as flask_app
from app.repositories.UsersRepository import UsersRepository
from app.services.security import (
    CSRF_TTL_SECONDS,
    decode_password_reset_token,
    enforce_csrf,
    generate_csrf_token,
    generate_password_reset_token,
    hash_password,
    sign_session,
)
from app.models.roles import RolesEnum
from app.models.users import Sex, SkinColor


def _unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _session_and_csrf_for_user(user_id: str):
    csrf_token = generate_csrf_token(user_id)
    session_token = sign_session(
        {"id": user_id, "email": f"{user_id}@example.com", "role": "User"}
    )
    cookie_header = (
        f"{settings.COOKIE_NAME}={session_token}; "
        f"{settings.CSRF_COOKIE_NAME}={csrf_token}"
    )
    headers = {"X-CSRF-Token": csrf_token}
    return csrf_token, cookie_header, headers


def test_enforce_csrf_accepts_valid_token():
    user_id = "42"
    csrf_token, cookie_header, headers = _session_and_csrf_for_user(user_id)

    with flask_app.test_request_context(
        "/protected",
        headers=headers,
        environ_overrides={"HTTP_COOKIE": cookie_header},
    ):
        enforce_csrf()  # should not raise


def test_enforce_csrf_rejects_mismatch():
    user_id = "43"
    csrf_token, cookie_header, headers = _session_and_csrf_for_user(user_id)
    headers["X-CSRF-Token"] = csrf_token + "tampered"

    with flask_app.test_request_context(
        "/protected",
        headers=headers,
        environ_overrides={"HTTP_COOKIE": cookie_header},
    ):
        with pytest.raises(Forbidden):
            enforce_csrf()


def test_enforce_csrf_rejects_expired_token(monkeypatch):
    user_id = "44"
    base_time = 1_000_000

    monkeypatch.setattr("app.services.security.time.time", lambda: base_time)
    csrf_token, cookie_header, headers = _session_and_csrf_for_user(user_id)

    monkeypatch.setattr(
        "app.services.security.time.time",
        lambda: base_time + CSRF_TTL_SECONDS + 10,
    )

    with flask_app.test_request_context(
        "/protected",
        headers=headers,
        environ_overrides={"HTTP_COOKIE": cookie_header},
    ):
        with pytest.raises(Forbidden):
            enforce_csrf()


def test_password_reset_token_roundtrip(db_session):
    repo = UsersRepository(db_session)
    email = _unique_email("reset")
    user = repo.CreateUser(
        email=email,
        password_hash=hash_password("SenhaForte@123"),
        name_for_certificate="Reset User",
        username=f"user_{uuid.uuid4().hex[:6]}",
        sex=Sex.NotSpecified,
        color=SkinColor.NotSpecified,
        role=RolesEnum.User,
    )

    token = generate_password_reset_token(user)
    data = decode_password_reset_token(token)
    assert data["user_id"] == user.user_id
    assert data["email"] == user.email


def test_password_reset_token_rejects_tampering(db_session):
    repo = UsersRepository(db_session)
    email = _unique_email("tamper")
    user = repo.CreateUser(
        email=email,
        password_hash=hash_password("OutraSenha@123"),
        name_for_certificate="Reset User",
        username=f"user_{uuid.uuid4().hex[:6]}",
        sex=Sex.NotSpecified,
        color=SkinColor.NotSpecified,
        role=RolesEnum.User,
    )

    token = generate_password_reset_token(user)
    tampered = token + "a"

    with pytest.raises(Unauthorized):
        decode_password_reset_token(tampered)
