from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request, abort
from pydantic import ValidationError

from app.core.db import get_db
from app.models.users import (
    RegisterIn,
    LoginIn,
    UserOut,
    User,
    ForgotPasswordIn,
    ResetPasswordIn,
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
    sign_password_reset_token,
    verify_password_reset_token,
)
from app.repositories.UsersRepository import UsersRepository
from app.services.email import send_welcome_email, send_password_reset_email


bp = Blueprint("auth", __name__, url_prefix="/auth")

logger = logging.getLogger(__name__)


def _validate_payload(model_cls):
    data = request.get_json(silent=True) or {}
    return model_cls.model_validate(data)


@bp.post("/register")
def register():
    try:
        payload: RegisterIn = _validate_payload(RegisterIn)
    except ValidationError as exc:
        return jsonify({"detail": exc.errors()}), 422

    db = get_db()
    repo = UsersRepository(db)

    if repo.ExistsEmail(payload.email):
        abort(409, description="Email já cadastrado")
    if repo.ExistsUsername(payload.username):
        abort(409, description="Username já cadastrado")

    user = repo.CreateUser(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name_for_certificate=payload.name_for_certificate,
        username=payload.username,
        sex=payload.sex,
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
    response = jsonify({"user": user_out})
    set_session_cookie(response, token, remember=payload.remember)
    csrf_token = generate_csrf_token(str(user.user_id))
    set_csrf_cookie(response, csrf_token, remember=payload.remember)
    response.headers["X-CSRF-Token"] = csrf_token

    try:
        send_welcome_email(user)
    except Exception:  # pragma: no cover - logging only
        logger.exception("Falha ao enviar email de boas-vindas para %s", user.email)

    return response


@bp.post("/login")
def login():
    try:
        payload: LoginIn = _validate_payload(LoginIn)
    except ValidationError as exc:
        return jsonify({"detail": exc.errors()}), 422

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


@bp.post("/forgot-password")
def forgot_password():
    try:
        payload: ForgotPasswordIn = _validate_payload(ForgotPasswordIn)
    except ValidationError as exc:
        return jsonify({"detail": exc.errors()}), 422

    db = get_db()
    repo = UsersRepository(db)
    user = repo.GetUserByEmail(payload.email)

    if user:
        token = sign_password_reset_token(user.user_id)
        try:
            send_password_reset_email(user, token)
        except Exception:  # pragma: no cover - logging only
            logger.exception(
                "Falha ao enviar email de redefinição de senha para %s", payload.email
            )

    return jsonify({"ok": True})


@bp.post("/reset-password")
def reset_password():
    try:
        payload: ResetPasswordIn = _validate_payload(ResetPasswordIn)
    except ValidationError as exc:
        return jsonify({"detail": exc.errors()}), 422

    try:
        user_id = verify_password_reset_token(payload.token)
    except ValueError:
        abort(400, description="Token inválido ou expirado")

    db = get_db()
    repo = UsersRepository(db)
    user = repo.GetUserById(user_id)

    if not user:
        abort(400, description="Token inválido ou expirado")

    repo.UpdatePassword(user, hash_password(payload.password))

    return jsonify({"ok": True})
