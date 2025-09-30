from __future__ import annotations

from typing import Optional

from flask import Blueprint, jsonify
from pydantic import BaseModel

from app.core.db import get_db
from app.repositories.UserTrailsRepository import UserTrailsRepository
from app.services.security import get_current_user_id


bp = Blueprint("user_trails", __name__, url_prefix="/user-trails")


class ProgressOut(BaseModel):
    done: int
    total: int
    computed_progress_percent: Optional[float] = None
    nextAction: Optional[str] = None
    enrolledAt: Optional[str] = None
    status: Optional[str] = None
    completed_at: Optional[str] = None


class ItemProgressOut(BaseModel):
    item_id: int
    status: Optional[str]
    progress_value: Optional[int]
    completed_at: Optional[str] = None


class SectionProgressOut(BaseModel):
    section_id: int
    title: str
    total: int
    done: int
    percent: float


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


@bp.get("/<int:trail_id>/items-progress")
def get_items_progress(trail_id: int):
    user_id = get_current_user_id()
    db = get_db()
    repo = UserTrailsRepository(db)
    repo.ensure_enrollment(user_id, trail_id)
    items = repo.get_items_progress(user_id, trail_id)
    return jsonify([ItemProgressOut(**item).model_dump(mode="json") for item in items])


@bp.get("/<int:trail_id>/sections-progress")
def get_sections_progress(trail_id: int):
    user_id = get_current_user_id()
    db = get_db()
    repo = UserTrailsRepository(db)
    repo.ensure_enrollment(user_id, trail_id)
    sections = repo.get_sections_progress(user_id, trail_id)
    return jsonify([SectionProgressOut(**section).model_dump(mode="json") for section in sections])
