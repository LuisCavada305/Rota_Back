from __future__ import annotations

from flask import Blueprint, jsonify, request, abort
from pydantic import ValidationError

from app.core.db import get_db
from app.models.users import RegisterIn, LoginIn, UserOut, User
from app.services.security import (
    hash_password,
    verify_password,
    sign_session,
    set_session_cookie,
    set_csrf_cookie,
    generate_csrf_token,
    clear_session_cookie,
    clear_csrf_cookie,
)
from app.repositories.UsersRepository import UsersRepository


bp = Blueprint("auth", __name__, url_prefix="/auth")


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
