from __future__ import annotations

from typing import Optional, List

from flask import Blueprint, jsonify
from pydantic import BaseModel

from app.core.db import get_db
from app.repositories.UserTrailsRepository import UserTrailsRepository
from app.services.security import get_current_user, enforce_csrf
from app.services.security import get_current_user_id
from app.services.email import send_trail_enrollment_email
from app.repositories.TrailsRepository import TrailsRepository


bp = Blueprint("user_trails", __name__, url_prefix="/user-trails")


class CertificateSummary(BaseModel):
    hash: str
    credential_id: str
    issued_at: Optional[str] = None


class ProgressOut(BaseModel):
    done: int
    total: int
    computed_progress_percent: Optional[float] = None
    nextAction: Optional[str] = None
    enrolledAt: Optional[str] = None
    status: Optional[str] = None
    completed_at: Optional[str] = None
    certificate: Optional[CertificateSummary] = None


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


class TrailOverviewOut(BaseModel):
    trail_id: int
    name: str
    thumbnail_url: str
    author: Optional[str] = None
    status: Optional[str] = None
    progress: ProgressOut


class OverviewOut(BaseModel):
    summary: dict
    trails: List[TrailOverviewOut]


@bp.get("/me/overview")
def get_user_overview():
    user_id = get_current_user_id()
    db = get_db()
    repo = UserTrailsRepository(db)
    trails_raw = repo.get_overview_for_user(user_id)

    enrolled_total = len(trails_raw)
    completed_total = 0
    active_total = 0
    trails_out: List[TrailOverviewOut] = []

    for item in trails_raw:
        progress_data = item.get("progress") or {}
        raw_status = progress_data.get("status") or item.get("status") or ""
        status_upper = raw_status.upper()

        progress_model = ProgressOut(**progress_data)
        if status_upper == "COMPLETED":
            completed_total += 1
        else:
            active_total += 1

        trails_out.append(
            TrailOverviewOut(
                trail_id=item["trail_id"],
                name=item["name"],
                thumbnail_url=item["thumbnail_url"],
                author=item.get("author"),
                status=progress_model.status or raw_status or None,
                progress=progress_model,
            )
        )

    summary = {
        "enrolled": enrolled_total,
        "active": active_total,
        "completed": completed_total,
    }

    payload = OverviewOut(
        summary=summary,
        trails=trails_out,
    )
    return jsonify(payload.model_dump(mode="json"))


@bp.get("/<int:trail_id>/progress")
def get_progress(trail_id: int):
    db = get_db()
    repo = UserTrailsRepository(db)
    data = repo.get_progress_for_current_user(trail_id)
    if not data:
        total = repo.count_items_in_trail(trail_id)
        default = ProgressOut(
            done=0,
            total=total,
            computed_progress_percent=0.0,
            nextAction="Começar",
            certificate=None,
        )
        return jsonify(default.model_dump(mode="json"))
    return jsonify(ProgressOut(**data).model_dump(mode="json"))


@bp.get("/<int:trail_id>/items-progress")
def get_items_progress(trail_id: int):
    user_id = get_current_user_id()
    db = get_db()
    repo = UserTrailsRepository(db)
    enrollment, _ = repo.ensure_enrollment(user_id, trail_id, create_if_missing=False)
    if enrollment is None:
        return (
            jsonify(
                {
                    "detail": "Você precisa se inscrever na trilha antes de acessar o progresso."
                }
            ),
            403,
        )
    items = repo.get_items_progress(user_id, trail_id)
    return jsonify([ItemProgressOut(**item).model_dump(mode="json") for item in items])


@bp.get("/<int:trail_id>/sections-progress")
def get_sections_progress(trail_id: int):
    user_id = get_current_user_id()
    db = get_db()
    repo = UserTrailsRepository(db)
    enrollment, _ = repo.ensure_enrollment(user_id, trail_id, create_if_missing=False)
    if enrollment is None:
        return (
            jsonify(
                {
                    "detail": "Você precisa se inscrever na trilha antes de acessar o progresso."
                }
            ),
            403,
        )
    sections = repo.get_sections_progress(user_id, trail_id)
    return jsonify(
        [SectionProgressOut(**section).model_dump(mode="json") for section in sections]
    )


@bp.post("/<int:trail_id>/enroll")
def enroll_in_trail(trail_id: int):
    enforce_csrf()
    user = get_current_user()
    db = get_db()
    repo = UserTrailsRepository(db)
    _, created = repo.ensure_enrollment(user.user_id, trail_id)
    if created:
        trail = TrailsRepository(db).get_trail(trail_id)
        if trail:
            send_trail_enrollment_email(
                email=user.email,
                name=user.name_for_certificate,
                trail_name=trail.name,
            )
    progress = repo.get_progress_for_user(user.user_id, trail_id) or {
        "done": 0,
        "total": repo.count_items_in_trail(trail_id),
        "computed_progress_percent": 0.0,
        "nextAction": "Começar",
        "enrolledAt": None,
        "status": "ENROLLED",
        "completed_at": None,
        "certificate": None,
    }
    first_item_id = repo.get_first_trail_item_id(trail_id)
    return jsonify(
        {
            "ok": True,
            "trail_id": trail_id,
            "first_item_id": first_item_id,
            "progress": progress,
        }
    )
