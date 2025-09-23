from __future__ import annotations

import jwt
from flask import Blueprint, jsonify, request, abort

from app.core.db import get_db
from app.core.settings import settings
from app.models.users import User, UserOut


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
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        abort(404, description="Usuário não encontrado")
    user_out = UserOut.from_orm_user(user).model_dump(mode="json")
    return jsonify({"user": user_out})
