from __future__ import annotations

import math

from flask import Blueprint, jsonify, request, abort
from werkzeug.exceptions import Unauthorized
from pydantic import ValidationError

from app.core.db import get_db
from app.models.users import (
    RegisterIn,
    LoginIn,
    UserOut,
    User,
    PasswordResetRequestIn,
    PasswordResetConfirmIn,
)
from app.services.security import (
    hash_password,
    verify_password,
    sign_session,
    set_session_cookie,
    set_csrf_cookie,
    generate_csrf_token,
    clear_session_cookie,
    clear_csrf_cookie,
    generate_password_reset_token,
    decode_password_reset_token,
)
from app.repositories.UsersRepository import UsersRepository
from app.services.rate_limiter import check_auth_rate_limit
from app.services.email import (
    send_welcome_email,
    send_password_reset_email,
    send_password_changed_notification,
)
from app.routes import format_validation_error


bp = Blueprint("auth", __name__, url_prefix="/auth")


def _client_identifier() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    ip = forwarded_for.split(",", 1)[0].strip() if forwarded_for else ""
    if not ip:
        ip = request.remote_addr or "unknown"
    return ip


def _rate_limited_response(scope: str, *, identifier: str | None = None):
    parts = [scope]
    if identifier:
        parts.append(identifier.lower())
    parts.append(_client_identifier())
    retry_after = check_auth_rate_limit(":".join(parts))
    if retry_after is None:
        return None
    wait_seconds = max(1, math.ceil(retry_after))
    payload = {"detail": "Muitas tentativas. Aguarde antes de tentar novamente."}
    response = jsonify(payload)
    response.status_code = 429
    response.headers["Retry-After"] = str(wait_seconds)
    return response


def _validate_payload(model_cls):
    data = request.get_json(silent=True) or {}
    return model_cls.model_validate(data)


@bp.post("/register")
def register():
    try:
        payload: RegisterIn = _validate_payload(RegisterIn)
    except ValidationError as exc:
        return jsonify({"detail": format_validation_error(exc)}), 422

    limited = _rate_limited_response(
        "register", identifier=f"{payload.email}:{payload.username}"
    )
    if limited:
        return limited

    db = get_db()
    repo = UsersRepository(db)

    if repo.ExistsEmail(payload.email) or repo.ExistsUsername(payload.username):
        abort(409, description="Dados já cadastrados")

    user = repo.CreateUser(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name_for_certificate=payload.name_for_certificate,
        username=payload.username,
        sex=payload.sex,
        color=payload.color,
        role=payload.role,
        birthday=payload.birthday,
        social_name=payload.social_name,
    )

    token = sign_session(
        {
            "id": user.user_id,
            "email": user.email,
            "role": user.role.code,
            "username": user.username,
        }
    )

    user_out = UserOut.from_orm_user(user).model_dump(mode="json")
    send_welcome_email(email=user.email, name=user.name_for_certificate)
    response = jsonify({"user": user_out})
    set_session_cookie(response, token, remember=payload.remember)
    csrf_token = generate_csrf_token(str(user.user_id))
    set_csrf_cookie(response, csrf_token, remember=payload.remember)
    response.headers["X-CSRF-Token"] = csrf_token
    return response


@bp.post("/password/forgot")
def forgot_password():
    try:
        payload: PasswordResetRequestIn = _validate_payload(PasswordResetRequestIn)
    except ValidationError as exc:
        return jsonify({"detail": format_validation_error(exc)}), 422

    limited = _rate_limited_response("password_reset", identifier=payload.email)
    if limited:
        return limited

    db = get_db()
    repo = UsersRepository(db)
    user = repo.GetUserByEmail(payload.email)
    if user:
        token = generate_password_reset_token(user)
        send_password_reset_email(
            email=user.email,
            name=user.name_for_certificate,
            token=token,
        )
    return jsonify({"ok": True})


@bp.post("/password/reset")
def reset_password():
    try:
        payload: PasswordResetConfirmIn = _validate_payload(PasswordResetConfirmIn)
    except ValidationError as exc:
        return jsonify({"detail": format_validation_error(exc)}), 422

    try:
        token_data = decode_password_reset_token(payload.token)
    except Unauthorized as exc:
        return jsonify({"detail": exc.description or "Token inválido"}), exc.code

    db = get_db()
    repo = UsersRepository(db)
    user = repo.GetUserByEmail(token_data["email"])
    if not user or user.user_id != token_data["user_id"]:
        return jsonify({"detail": "Token inválido"}), 401

    repo.UpdatePassword(user, hash_password(payload.new_password))
    send_password_changed_notification(
        email=user.email,
        name=user.name_for_certificate,
    )
    return jsonify({"ok": True})


@bp.post("/login")
def login():
    try:
        payload: LoginIn = _validate_payload(LoginIn)
    except ValidationError as exc:
        return jsonify({"detail": format_validation_error(exc)}), 422

    limited = _rate_limited_response("login", identifier=payload.email)
    if limited:
        return limited

    db = get_db()
    repo = UsersRepository(db)
    user: User | None = repo.GetUserByEmail(payload.email)

    if not user or not verify_password(payload.password, user.password_hash):
        abort(401, description="Credenciais inválidas")

    token = sign_session(
        {
            "id": user.user_id,
            "email": user.email,
            "role": user.role.code,
            "username": user.username,
        }
    )

    user_out = UserOut.from_orm_user(user).model_dump(mode="json")
    response = jsonify({"user": user_out})
    set_session_cookie(response, token, remember=payload.remember)
    csrf_token = generate_csrf_token(str(user.user_id))
    set_csrf_cookie(response, csrf_token, remember=payload.remember)
    response.headers["X-CSRF-Token"] = csrf_token
    return response


@bp.post("/logout")
def logout():
    response = jsonify({"ok": True})
    clear_session_cookie(response)
    clear_csrf_cookie(response)
    return response
