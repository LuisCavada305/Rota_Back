from __future__ import annotations

import jwt
from flask import Blueprint, jsonify, request, abort
from sqlalchemy.orm import joinedload, load_only
from pydantic import BaseModel, ValidationError, field_validator

from app.core.db import get_db
from app.core.settings import settings
from app.models.users import User, UserOut
from app.models.lookups import LkRole, LkSex, LkColor
from app.repositories.UsersRepository import UsersRepository
from app.routes import format_validation_error


bp = Blueprint("me", __name__)


class ProfileOut(BaseModel):
    username: str
    name_for_certificate: str
    social_name: str | None = None


class ProfileUpdateIn(BaseModel):
    name_for_certificate: str

    @field_validator("name_for_certificate")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Informe um nome para o certificado.")
        return value.strip()


def get_current_user_id(req=None) -> str:
    req = req or request
    token = req.cookies.get(settings.COOKIE_NAME)
    if not token:
        abort(401, description="Não autenticado")
    try:
        decoded = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )
        return decoded["id"]
    except jwt.PyJWTError:
        abort(401, description="Sessão inválida")


@bp.get("/me")
def me():
    user_id = get_current_user_id()
    db = get_db()
    user = (
        db.query(User)
        .options(
            load_only(
                User.user_id,
                User.email,
                User.username,
                User.profile_pic_url,
                User.banner_pic_url,
            ),
            joinedload(User.role).load_only(LkRole.code),
            joinedload(User.sex).load_only(LkSex.code),
            joinedload(User.color).load_only(LkColor.code),
        )
        .filter(User.user_id == user_id)
        .first()
    )
    if not user:
        abort(404, description="Usuário não encontrado")
    user_out = UserOut.from_orm_user(user).model_dump(mode="json")
    response = jsonify({"user": user_out})
    csrf_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    if csrf_token:
        response.headers["X-CSRF-Token"] = csrf_token
    return response


def _load_profile_user(user_id):
    db = get_db()
    user = (
        db.query(User)
        .options(
            load_only(
                User.user_id,
                User.username,
                User.name_for_certificate,
                User.social_name,
            )
        )
        .filter(User.user_id == user_id)
        .first()
    )
    return db, user


@bp.get("/me/profile")
def profile():
    user_id = get_current_user_id()
    db, user = _load_profile_user(user_id)
    if not user:
        abort(404, description="Usuário não encontrado")
    profile_out = ProfileOut(
        username=user.username,
        name_for_certificate=user.name_for_certificate,
        social_name=user.social_name,
    )
    response = jsonify({"profile": profile_out.model_dump(mode="json")})
    csrf_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    if csrf_token:
        response.headers["X-CSRF-Token"] = csrf_token
    return response


@bp.patch("/me/profile")
def update_profile():
    user_id = get_current_user_id()
    try:
        payload = ProfileUpdateIn.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"detail": format_validation_error(exc)}), 422

    db, user = _load_profile_user(user_id)
    if not user:
        abort(404, description="Usuário não encontrado")

    repo = UsersRepository(db)
    updated = repo.UpdateCertificateName(
        user, name_for_certificate=payload.name_for_certificate
    )
    profile_out = ProfileOut(
        username=updated.username,
        name_for_certificate=updated.name_for_certificate,
        social_name=updated.social_name,
    )
    return jsonify({"profile": profile_out.model_dump(mode="json")})
