from __future__ import annotations

from typing import Optional

from flask import Blueprint, jsonify
from pydantic import BaseModel

from app.core.db import get_db
from app.repositories.UserTrailsRepository import UserTrailsRepository


bp = Blueprint("user_trails", __name__, url_prefix="/user-trails")


class ProgressOut(BaseModel):
    done: int
    total: int
    computed_progress_percent: Optional[float] = None
    nextAction: Optional[str] = None
    enrolledAt: Optional[str] = None


@bp.get("/<int:trail_id>/progress")
def get_progress(trail_id: int):
    db = get_db()
    repo = UserTrailsRepository(db)
    data = repo.get_progress_for_current_user(trail_id)
    if not data:
        total = repo.count_items_in_trail(trail_id)
        default = ProgressOut(
            done=0, total=total, computed_progress_percent=0.0, nextAction="Começar"
        )
        return jsonify(default.model_dump(mode="json"))
    return jsonify(ProgressOut(**data).model_dump(mode="json"))
