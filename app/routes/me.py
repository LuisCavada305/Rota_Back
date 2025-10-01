from __future__ import annotations

import jwt
from flask import Blueprint, jsonify, request, abort
from sqlalchemy.orm import joinedload, load_only

from app.core.db import get_db
from app.core.settings import settings
from app.models.users import User, UserOut
from app.models.lookups import LkRole, LkSex


bp = Blueprint("me", __name__)


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
