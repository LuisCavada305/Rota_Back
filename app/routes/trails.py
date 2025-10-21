from __future__ import annotations

from typing import List, Optional, Literal
import math

from flask import Blueprint, jsonify, abort, request
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import selectinload

from werkzeug.exceptions import Unauthorized

from app.core.db import get_db
from app.models.trail_items import TrailItems as TrailItemsORM
from app.models.user_item_progress import UserItemProgress as UserItemProgressORM
from app.repositories.TrailsRepository import TrailsRepository
from app.repositories.UserProgressRepository import UserProgressRepository
from app.repositories.UserTrailsRepository import UserTrailsRepository
from app.services.security import get_current_user, enforce_csrf, get_current_user_id
from app.routes import format_validation_error


bp = Blueprint("trails", __name__, url_prefix="/trails")

# ===== Schemas =====


class TrailOut(BaseModel):
    id: int
    name: str
    thumbnail_url: str
    author: Optional[str] = None
    review: Optional[float] = None
    review_count: Optional[int] = None
    description: Optional[str] = None
    progress_percent: Optional[float] = None
    status: Optional[str] = None
    completed_at: Optional[str] = None
    is_completed: Optional[bool] = None
    nextAction: Optional[str] = None
    user_review_rating: Optional[int] = None
    user_review_comment: Optional[str] = None

    class Config:
        from_attributes = True


class ItemOut(BaseModel):
    id: int
    title: str
    duration_seconds: Optional[int] = None
    order_index: Optional[int] = 0
    type: Optional[str] = None
    requires_completion: bool = False

    class Config:
        from_attributes = True


class SectionOut(BaseModel):
    id: int
    title: str
    order_index: Optional[int] = 0

    class Config:
        from_attributes = True


class SectionWithItemsOut(SectionOut):
    items: List[ItemOut]


class TextValOut(BaseModel):
    text_val: str


def _build_locked_response(blocked_item: dict):
    title = (blocked_item.get("title") or "").strip()
    return (
        jsonify(
            {
                "detail": "Conclua o item obrigatório antes de prosseguir.",
                "reason": "item_locked",
                "blocked_item": {
                    "id": blocked_item.get("id"),
                    "title": title,
                },
            }
        ),
        423,
    )


def _parse_positive_int(value: str | None, default: int, *, minimum: int = 1) -> int:
    try:
        if value is None:
            return default
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= minimum else default


def _build_pagination_metadata(page: int, page_size: int, total: int) -> dict:
    pages = (total + page_size - 1) // page_size if page_size else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
    }


def _attach_progress_metadata(db, trail_payload: List[dict]) -> List[dict]:
    try:
        user_id = get_current_user_id()
    except Unauthorized:
        return trail_payload

    repo = UserTrailsRepository(db)
    trail_ids = [int(item["id"]) for item in trail_payload]
    progress_map = repo.get_progress_map_for_user(user_id, trail_ids, sync=False)

    for item in trail_payload:
        progress = progress_map.get(int(item["id"]))
        if not progress:
            continue
        item["progress_percent"] = progress.get("computed_progress_percent")
        item["status"] = progress.get("status")
        item["completed_at"] = progress.get("completed_at")
        item["is_completed"] = progress.get("status") == "COMPLETED"
        item["nextAction"] = progress.get("nextAction")
        item["user_review_rating"] = progress.get("review_rating")
        item["user_review_comment"] = progress.get("review_comment")
    return trail_payload


@bp.get("/showcase")
def get_trails_showcase():
    db = get_db()
    repo = TrailsRepository(db)
    trails = repo.list_showcase()
    data = [
        TrailOut.model_validate(t, from_attributes=True).model_dump(mode="json")
        for t in trails
    ]
    data = _attach_progress_metadata(db, data)
    return jsonify({"trails": data})


@bp.get("/")
def get_trails():
    db = get_db()
    repo = TrailsRepository(db)
    page = _parse_positive_int(request.args.get("page"), 1)
    page_size = _parse_positive_int(request.args.get("page_size"), 10)
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    trails, total = repo.list_all(offset=offset, limit=page_size)
    data = [
        TrailOut.model_validate(t, from_attributes=True).model_dump(mode="json")
        for t in trails
    ]
    data = _attach_progress_metadata(db, data)
    return jsonify(
        {
            "trails": data,
            "pagination": _build_pagination_metadata(page, page_size, total),
        }
    )


@bp.get("/<int:trail_id>")
def get_trail(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    t = repo.get_trail(trail_id)
    if not t:
        abort(404, description="Trail not found")
    data = TrailOut.model_validate(t, from_attributes=True).model_dump(mode="json")
    data = _attach_progress_metadata(db, [data])[0]
    return jsonify(data)


class ReviewPayload(BaseModel):
    rating: int
    comment: Optional[str] = None


@bp.post("/<int:trail_id>/reviews")
def submit_trail_review(trail_id: int):
    enforce_csrf()
    user = get_current_user()
    if not user:
        abort(401)

    try:
        payload = ReviewPayload.model_validate(request.get_json(force=True) or {})
    except ValidationError as exc:
        return format_validation_error(exc)

    db = get_db()
    repo = UserTrailsRepository(db)
    try:
        result = repo.save_review(
            user.user_id,
            trail_id,
            payload.rating,
            payload.comment,
        )
    except PermissionError:
        abort(403, description="Finalize a trilha para poder avaliá-la.")
    except ValueError as exc:
        abort(400, description=str(exc))

    return jsonify(
        {
            "ok": True,
            "rating": result.get("rating"),
            "comment": result.get("comment"),
            "average": result.get("average"),
            "count": result.get("count"),
        }
    )


@bp.get("/<int:trail_id>/sections")
def get_sections(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    page = _parse_positive_int(request.args.get("page"), 1)
    page_size = _parse_positive_int(request.args.get("page_size"), 20)
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    secs, total = repo.list_sections(trail_id, offset=offset, limit=page_size)
    data = [
        SectionOut.model_validate(s, from_attributes=True).model_dump(mode="json")
        for s in secs
    ]
    return jsonify(
        {
            "sections": data,
            "pagination": _build_pagination_metadata(page, page_size, total),
        }
    )


@bp.get("/<int:trail_id>/sections/<int:section_id>/items")
def get_section_items(trail_id: int, section_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    page = _parse_positive_int(request.args.get("page"), 1)
    page_size = _parse_positive_int(request.args.get("page_size"), 25)
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    items, total = repo.list_section_items(
        trail_id, section_id, offset=offset, limit=page_size
    )
    data = [
        ItemOut(
            id=i.id,
            title=i.title or "",
            duration_seconds=i.duration_seconds,
            order_index=i.order_index,
            type=(i.type.code if i.type else None),
            requires_completion=i.completion_required(),
        ).model_dump(mode="json")
        for i in items
    ]
    return jsonify(
        {
            "items": data,
            "pagination": _build_pagination_metadata(page, page_size, total),
        }
    )


@bp.get("/<int:trail_id>/sections-with-items")
def get_sections_with_items(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    secs = repo.list_sections_with_items(trail_id)
    out: List[SectionWithItemsOut] = []
    for s in secs:
        out.append(
            SectionWithItemsOut(
                id=s.id,
                title=s.title,
                order_index=s.order_index,
                items=[
                    ItemOut(
                        id=i.id,
                        title=i.title or "",
                        duration_seconds=i.duration_seconds,
                        order_index=i.order_index,
                        type=(i.type.code if i.type else None),
                        requires_completion=i.completion_required(),
                    )
                    for i in s.items
                ],
            )
        )
    data = [section.model_dump(mode="json") for section in out]
    return jsonify(data)


@bp.get("/<int:trail_id>/included-items")
def get_included_items(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    rows = repo.list_included_items(trail_id)
    data = [TextValOut(text_val=r.text_val).model_dump(mode="json") for r in rows]
    return jsonify(data)


@bp.get("/<int:trail_id>/requirements")
def get_requirements(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    rows = repo.list_requirements(trail_id)
    data = [TextValOut(text_val=r.text_val).model_dump(mode="json") for r in rows]
    return jsonify(data)


@bp.get("/<int:trail_id>/audience")
def get_audience(trail_id: int):
    db = get_db()
    repo = TrailsRepository(db)
    rows = repo.list_audience(trail_id)
    data = [TextValOut(text_val=r.text_val).model_dump(mode="json") for r in rows]
    return jsonify(data)


@bp.get("/<int:trail_id>/learn")
def get_learn(trail_id: int):
    _ = trail_id
    return jsonify([])


class ItemProgressIn(BaseModel):
    status: Literal["IN_PROGRESS", "COMPLETED"]
    progress_value: int | None = None  # % ou segundos, escolha um padrão


@bp.put("/<int:trail_id>/items/<int:item_id>/progress")
def set_item_progress(trail_id: int, item_id: int):
    data = request.get_json(silent=True) or {}
    try:
        body = ItemProgressIn.model_validate(data)
    except ValidationError as exc:
        return jsonify({"detail": format_validation_error(exc)}), 422

    enforce_csrf()
    user = get_current_user()
    db = get_db()

    item = (
        db.query(TrailItemsORM)
        .options(selectinload(TrailItemsORM.type))
        .filter_by(id=item_id, trail_id=trail_id)
        .first()
    )
    if not item:
        abort(404, description="Item não encontrado na trilha")

    user_trails_repo = UserTrailsRepository(db)
    blocker = user_trails_repo.find_blocking_item(user.user_id, trail_id, item_id)
    if blocker:
        return _build_locked_response(blocker)

    item_type = item.type.code if item.type is not None else "DOC"
    duration_seconds = item.duration_seconds or 0
    required_percentage = getattr(item, "required_percentage", None) or 70

    # progresso anterior registrado
    existing_progress = (
        db.query(UserItemProgressORM)
        .filter(
            UserItemProgressORM.user_id == user.user_id,
            UserItemProgressORM.trail_item_id == item_id,
        )
        .first()
    )
    existing_seconds = 0
    if existing_progress and existing_progress.progress_value is not None:
        existing_seconds = max(0, existing_progress.progress_value)

    reported_seconds = max(0, body.progress_value or 0)
    effective_seconds = max(existing_seconds, reported_seconds)
    if duration_seconds:
        effective_seconds = min(effective_seconds, duration_seconds)

    is_privileged = user.role_code in {"Admin", "Manager"}

    if item_type == "VIDEO" and not is_privileged:
        skip_ahead_window = (
            max(30, int(duration_seconds * 0.1)) if duration_seconds else 30
        )
        if reported_seconds > existing_seconds:
            delta = reported_seconds - existing_seconds
            if delta > skip_ahead_window and body.status != "COMPLETED":
                return (
                    jsonify(
                        {
                            "detail": "Você não pode adiantar o vídeo. Assista na ordem para registrar o progresso.",
                            "reason": "skip_ahead_blocked",
                        }
                    ),
                    403,
                )

        if body.status == "COMPLETED" and duration_seconds:
            required_seconds = math.ceil(duration_seconds * (required_percentage / 100))
            tolerance = max(5, int(duration_seconds * 0.05))
            target = min(required_seconds, duration_seconds)
            if effective_seconds + tolerance < target:
                return (
                    jsonify(
                        {
                            "detail": "Finalize o vídeo antes de marcar como concluído.",
                            "reason": "insufficient_watch_time",
                        }
                    ),
                    422,
                )

    user_trails_repo.ensure_enrollment(user.user_id, trail_id)
    UserProgressRepository(db).upsert_item_progress(
        user.user_id,
        item_id,
        body.status,
        progress_value=(
            effective_seconds if item_type == "VIDEO" else body.progress_value
        ),
    )
    return jsonify({"ok": True})
